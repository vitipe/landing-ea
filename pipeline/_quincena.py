"""Procesa una quincena de punta a punta: escenas, índices, cifras y, si alcanza, rásters."""
import time

import dask
import geopandas as gpd

import _s2
import _salidas
import config

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def leer_partidos():
    partidos = gpd.read_file(config.PARTIDOS_GEOJSON).to_crs("EPSG:4326")
    return partidos.sort_values("nombre").reset_index(drop=True)


def nombre_quincena(desde):
    orden = "1.ª" if desde.day == 1 else "2.ª"
    return f"{orden} quincena de {MESES[desde.month - 1]} de {desde.year}"


def procesar(desde, hasta, partidos, rasters=True):
    """Devuelve (filas por partido, entrada para quincenas.json).

    Con rasters=True y suficiente dato en la zona, escribe los COG en salida/.
    """
    t0 = time.time()
    qid = desde.isoformat()
    zona = partidos.geometry.union_all()
    items = _s2.buscar(desde, hasta, zona)
    print(f"{qid}: {len(items)} escenas con menos de {config.NUBES_MAX_ESCENA}% de nubes")
    entrada = {"id": qid, "desde": qid, "hasta": hasta.isoformat(), "publicada": False,
               "escenas": [], "valido_pct": 0}
    if not items:
        entrada["motivo"] = "sin imágenes útiles"
        return {}, entrada

    idx, mascara, geobox = _s2.cubo(items, zona)
    mediana, n_obs, aporte = _s2.componer(idx, mascara)
    with dask.config.set(scheduler="threads", num_workers=_s2.HILOS_LECTURA):
        mediana, n_obs, aporte = dask.compute(mediana, n_obs, aporte)
    print(f"{qid}: cubo {dict(idx.sizes)} calculado en {time.time() - t0:.0f} s")

    calculo = partidos.to_crs(config.CRS_CALCULO)
    etiq = _salidas.etiquetas(calculo, geobox)
    valores = {k: mediana[k].values for k in mediana.data_vars}
    filas, valido_zona = _salidas.estadisticas(valores, n_obs.values, etiq, list(partidos["nombre"]),
                                               _salidas.agua_habitual(geobox))

    entrada["escenas"] = sorted({str(t)[:10] for t, n in zip(aporte.time.values, aporte.values) if n > 0})
    entrada["valido_pct"] = int(round(100 * valido_zona))
    print(f"{qid}: {entrada['valido_pct']}% de la zona con dato; pasadas útiles {entrada['escenas']}")

    if valido_zona < config.MIN_VALIDO_ZONA:
        entrada["motivo"] = "nubes"
        return filas, entrada
    if not rasters:
        return filas, entrada

    archivos = {}
    for indice in mediana.data_vars:
        ruta = _salidas.guardar_cog(mediana[indice], etiq, config.SALIDA / f"{indice}_{qid}.tif")
        archivos[indice] = f"cog/{ruta.name}"
        print(f"  {ruta.name}: {ruta.stat().st_size / 1e6:.1f} MB")
    entrada["publicada"] = True
    entrada["archivos"] = archivos
    entrada["og"] = imagen_og(mediana["ndvi"], etiq, calculo, desde)
    print(f"{qid}: listo en {time.time() - t0:.0f} s")
    return filas, entrada


def imagen_og(ndvi, etiq, calculo, desde):
    ruta = config.SALIDA / f"og_{desde.isoformat()}.jpg"
    texto = nombre_quincena(desde)
    _salidas.imagen_og(ndvi, etiq, calculo, texto[0].upper() + texto[1:], ruta)
    return f"cog/{ruta.name}"
