"""Sentinel-2 L2A de Earth Search: búsqueda, carga, máscara de nubes e índices."""
import warnings

import dask.array as dsa
import numpy as np
import odc.stac
import xarray as xr
from odc.geo.geom import Geometry
from pystac_client import Client
from shapely.geometry import mapping

import config

SCL_NUBES = [3, 8, 9, 10]        # sombra de nube, nube media, nube alta, cirro: se dilatan

odc.stac.configure_rio(
    cloud_defaults=True,
    GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="3",
    GDAL_HTTP_VERSION="2", GDAL_HTTP_MULTIPLEX="YES",        # reusa conexiones: pesa más la latencia que el ancho de banda
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
)
HILOS_LECTURA = 16               # la carga espera red, no CPU


def bandas_reflectancia():
    return sorted({b for par in config.INDICES.values() for b in par})


def _pasada(item):
    """(tesela MGRS, día): identifica la misma pasada en las dos colecciones."""
    p = item.properties
    return p["mgrs:utm_zone"], p["mgrs:latitude_band"], p["mgrs:grid_square"], item.datetime.date()


def _prioridad(item):
    """Mayor es mejor: primero COLECCION, después el procesamiento más nuevo."""
    return item.collection_id == config.COLECCION, item.properties.get("s2:processing_baseline", "")


def buscar(desde, hasta, zona):
    """Escenas entre dos fechas (inclusive) que tocan la zona (lon/lat), una por pasada.

    Busca en COLECCION y en COLECCION_RESPALDO; si una pasada está en las dos (o
    repetida con otro procesamiento), queda la de _prioridad.
    Con el polígono y no con el bbox: la zona es diagonal y el bbox suma teselas de
    las esquinas que no tocan ningún partido.
    """
    cliente = Client.open(config.STAC_URL)
    busqueda = cliente.search(
        collections=[config.COLECCION, config.COLECCION_RESPALDO], intersects=mapping(zona.simplify(0.01)),
        datetime=f"{desde}T00:00:00Z/{hasta}T23:59:59Z",
        query={"eo:cloud_cover": {"lt": config.NUBES_MAX_ESCENA}},
    )
    por_pasada = {}
    for it in busqueda.items():
        clave = _pasada(it)
        if clave not in por_pasada or _prioridad(it) > _prioridad(por_pasada[clave]):
            por_pasada[clave] = it
    items = list(por_pasada.values())
    faltan = {b for it in items for b in bandas_reflectancia() + ["scl"] if b not in it.assets}
    if faltan:
        raise SystemExit(f"Las escenas no traen los assets {sorted(faltan)}: revisá COLECCION e INDICES")
    return items


def _escala(item, banda):
    meta = item.assets[banda].extra_fields
    rb = (meta.get("raster:bands") or meta.get("bands") or [{}])[0]
    return rb.get("scale", 1.0), rb.get("offset", 0.0)


def cargar(items, zona):
    """Cubo (time, y, x) en la grilla de cálculo; una capa por pasada (solar_day)."""
    return odc.stac.load(
        items,
        bands=bandas_reflectancia() + ["scl"],
        geopolygon=Geometry(zona, "EPSG:4326"),
        crs=config.CRS_CALCULO,
        resolution=config.RESOLUCION_M,
        groupby="solar_day",
        chunks={"x": config.CHUNK_PX, "y": config.CHUNK_PX},
        resampling={"scl": "nearest", "*": "average"},
    )


def reflectancia(ds, items):
    """Aplica scale y offset de raster:bands (en Collection 1: 0.0001 y -0.1). 0 = sin dato."""
    salida = {}
    for b in bandas_reflectancia():
        valores = {_escala(it, b) for it in items}
        if len(valores) != 1:
            raise SystemExit(f"{b}: scale/offset distintos entre escenas: {valores}")
        scale, offset = valores.pop()
        da = ds[b]
        salida[b] = xr.where(da != 0, da.astype("float32") * scale + offset, np.nan).clip(min=0)
    return xr.Dataset(salida)


def _dilatar_bloque(bloque, r):
    salida = bloque.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            salida |= np.roll(bloque, (dy, dx), axis=(-2, -1))
    return salida


def enmascarar(ds):
    """True donde el píxel es útil: SCL válida y lejos de nubes y sombras."""
    scl = ds["scl"]
    valido = scl.isin(config.SCL_VALIDAS)
    r = config.DILATAR_NUBES_PX
    if r:
        nubes = scl.isin(SCL_NUBES).data
        nubes = dsa.map_overlap(_dilatar_bloque, nubes, depth={0: 0, 1: r, 2: r},
                                boundary=False, r=r, dtype=bool)
        valido = valido & ~xr.DataArray(nubes, coords=scl.coords, dims=scl.dims)
    return valido


def indices(refl, mascara):
    """Diferencias normalizadas de config.INDICES, NaN donde no hay dato útil."""
    salida = {}
    for nombre, (a, b) in config.INDICES.items():
        nd = ((refl[a] - refl[b]) / (refl[a] + refl[b])).clip(-1, 1)
        salida[nombre] = nd.where(mascara)
    return xr.Dataset(salida)


def componer(idx, mascara):
    """Mediana de la quincena, observaciones útiles por píxel y píxeles útiles por pasada."""
    idx = idx.chunk({"time": -1})
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "All-NaN slice")
        mediana = idx.median("time", skipna=True)
    n_obs = mascara.sum("time").astype("uint8")
    aporte = mascara.sum(["y", "x"])
    return mediana, n_obs, aporte
