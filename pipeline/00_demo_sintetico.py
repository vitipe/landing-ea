"""Datos inventados para desarrollar la página del monitor sin bajar imágenes.

Uso (desde la raíz del repo):
    python pipeline/00_demo_sintetico.py
    python3 armar_sitio.py && python3 -m http.server 8000 -d _site   # /monitor/

Pisa monitor/data/serie.json y quincenas.json con "demo": true (la página muestra
un aviso y armar_sitio.py --release se niega a publicarlos). Para volver a los
datos reales: git checkout monitor/data
"""
from datetime import date

import numpy as np
import pyproj
from odc.geo.geobox import GeoBox
from odc.geo.xr import xr_zeros

import _alertas
import _datos
import _quincena
import _salidas
import config

RES_DEMO_M = 300                 # grilla gruesa: alcanza para ver la página
LAGUNAS = [(-62.80, -37.12, 9), (-62.45, -37.00, 7), (-62.33, -36.90, 5),   # (lon, lat, radio km)
           (-62.20, -36.80, 5), (-62.95, -36.60, 4), (-62.10, -37.30, 3)]
rng = np.random.default_rng(7)

partidos = _quincena.leer_partidos()
nombres = list(partidos["nombre"])
calculo = partidos.to_crs(config.CRS_CALCULO)
geobox = GeoBox.from_bbox(calculo.total_bounds, config.CRS_CALCULO, resolution=RES_DEMO_M)
etiq = _salidas.etiquetas(calculo, geobox)
base = xr_zeros(geobox, dtype="float32")
xx, yy = np.meshgrid(base.x.values, base.y.values)


def campo_suave(n=6, escala=40_000):
    """Suma de ondas al azar: manchas de 20 a 60 km, como lotes y ambientes."""
    z = np.zeros_like(xx)
    for _ in range(n):
        kx, ky = rng.normal(0, 2 * np.pi / escala, 2)
        z += np.sin(kx * xx + ky * yy + rng.uniform(0, 2 * np.pi))
    return z / n


def agua(humedad):
    """MNDWI: lagunas fijas que crecen con la humedad del período."""
    a_utm = pyproj.Transformer.from_crs("EPSG:4326", config.CRS_CALCULO, always_xy=True)
    m = -0.45 + 0.08 * campo_suave()
    for lon, lat, radio in LAGUNAS:
        cx, cy = a_utm.transform(lon, lat)
        d = np.hypot(xx - cx, yy - cy) / (radio * 1000 * (0.6 + humedad))
        m = np.maximum(m, 0.6 - 0.8 * d ** 2)
    return np.clip(m, -1, 1)


def estacion(q):
    """0 a 1: vigor esperado por época del año (pico en primavera y fin de verano)."""
    dia = q.timetuple().tm_yday
    return 0.5 + 0.5 * np.cos(2 * np.pi * (dia - 300) / 365)


def humedad_anio(anio):
    return {2017: 1.0, 2018: 0.8, 2019: 0.6, 2022: 0.15, 2023: 0.05}.get(anio, 0.45)


# --- Serie: 2017 hasta la última quincena cerrada ----------------------------------
hoy = date.today()
ultima = _datos.ultima_cerrada(hoy)
filas = {}
base_partido = {n: rng.uniform(-0.05, 0.05) for n in nombres}
for anio in range(2017, hoy.year + 1):
    for q in _datos.quincenas_del_anio(anio, hasta=hoy):
        h = humedad_anio(anio)
        filas[q.isoformat()] = {}
        for n in nombres:
            valido = int(np.clip(rng.normal(80, 25), 0, 100))
            ok = valido >= 100 * config.MIN_VALIDO_PARTIDO
            ndvi = 0.25 + 0.4 * estacion(q) + 0.1 * (h - 0.45) + base_partido[n] + rng.normal(0, 0.02)
            filas[q.isoformat()][n] = {
                "ndvi": round(ndvi, 3) if ok else None,
                "ndmi": round(ndvi * 0.6 - 0.12 + 0.1 * (h - 0.45), 3) if ok else None,
                "agua_km2": round(40 + 260 * h ** 2 + rng.normal(0, 8), 1) if ok else None,
                "agua_transitoria_km2": round(max(0, 120 * (h - 0.5)) + abs(rng.normal(0, 2)), 1) if ok else None,
                "valido_pct": valido,
            }
_datos.escribir_serie(filas, nombres, demo=True)
_alertas.escribir(filas, nombres, demo=True)

# --- Rásters: las últimas cuatro quincenas publicadas y una nublada más nueva -------
config.QUINCENAS_JSON.unlink(missing_ok=True)
inicios = [ultima]
while len(inicios) < 5:
    previo = inicios[-1]
    inicios.append(previo.replace(day=1) if previo.day == 16 else _datos.ultima_cerrada(previo))
for k, inicio in enumerate(reversed(inicios)):
    desde, hasta = _datos.quincena(inicio)
    qid = desde.isoformat()
    entrada = {"id": qid, "desde": qid, "hasta": hasta.isoformat(), "publicada": False,
               "escenas": [desde.replace(day=desde.day + d).isoformat() for d in (1, 6, 11)],
               "valido_pct": 4}
    if inicio != ultima:
        h = humedad_anio(desde.year)
        nubes = campo_suave(4, 25_000) > 0.55
        ndvi = 0.25 + 0.4 * estacion(desde) + 0.18 * campo_suave(8, 15_000)
        mndwi = agua(h)
        ndvi = np.where(mndwi > 0, -0.2, ndvi)
        indices = {"ndvi": ndvi, "mndwi": mndwi, "ndmi": ndvi * 0.6 - 0.12 + 0.05 * campo_suave()}
        archivos = {}
        for nombre, v in indices.items():
            da = base.copy(data=np.where(nubes, np.nan, v).astype("float32"))
            ruta = _salidas.guardar_cog(da, etiq, config.SALIDA / f"{nombre}_{qid}.tif")
            archivos[nombre] = f"cog/{ruta.name}"
        entrada.update(publicada=True, archivos=archivos, valido_pct=int(100 * (1 - nubes.mean())))
        entrada["og"] = _quincena.imagen_og(base.copy(data=np.where(nubes, np.nan, ndvi)), etiq, calculo, desde)
    else:
        entrada["motivo"] = "nubes"
    _datos.registrar_quincena(entrada, demo=True)
    print(f"{qid}: {'publicada' if entrada['publicada'] else 'nublada'}")
print(f"Demo lista: {len(filas)} quincenas en serie.json, rásters en {config.SALIDA}")
