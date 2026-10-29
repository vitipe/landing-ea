"""Paso 3 (una vez): máscara de lagunas habituales a partir del JRC Global Surface Water.

Uso (desde la raíz del repo):
    python pipeline/03_agua_habitual.py

Lee del JRC (1984-2024) solo la ventana de los partidos y guarda pipeline/datos/agua_habitual.tif:
1 donde hubo agua en al menos OCURRENCIA_HABITUAL % de las observaciones, 0 en el resto,
en EPSG:4326 y a la resolución del JRC (~25 m). _salidas.agua_habitual() la lleva a la grilla
de cálculo. Con eso, el agua de cada quincena se separa en lagunas y agua en los campos, y las
lagunas quedan fuera del promedio de NDVI y NDMI. Se commitea: no hay que volver a correrlo
salvo que cambien los partidos o el umbral.
"""
import numpy as np
import rasterio
from rasterio.windows import from_bounds

import _quincena
import config

MARGEN = 0.02                    # grados alrededor de los partidos

partidos = _quincena.leer_partidos()
oeste, sur, este, norte = partidos.total_bounds
# El archivo está guardado por filas y sin pirámides: bloques grandes para pedir pocos rangos
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_CHUNK_SIZE=str(10 * 2**20),
                  GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="5"):
    with rasterio.open(f"/vsicurl/{config.JRC_OCURRENCIA_URL}") as src:
        ventana = from_bounds(oeste - MARGEN, sur - MARGEN, este + MARGEN, norte + MARGEN, transform=src.transform)
        ventana = ventana.round_offsets().round_lengths()
        ocurrencia = src.read(1, window=ventana)
        transform = src.window_transform(ventana)
        crs = src.crs

# En el JRC, 255 es sin dato (fuera de la tierra observada): cuenta como no laguna
habitual = ((ocurrencia >= config.OCURRENCIA_HABITUAL) & (ocurrencia <= 100)).astype("uint8")
config.AGUA_HABITUAL_TIF.parent.mkdir(parents=True, exist_ok=True)
with rasterio.open(config.AGUA_HABITUAL_TIF, "w", driver="GTiff", width=habitual.shape[1], height=habitual.shape[0],
                   count=1, dtype="uint8", crs=crs, transform=transform, compress="deflate", tiled=True,
                   nbits=1) as dst:
    dst.write(habitual, 1)
px_km2 = abs(transform.a * transform.e) * (111.32 ** 2) * np.cos(np.radians((sur + norte) / 2))
print(f"{config.AGUA_HABITUAL_TIF.name}: {habitual.shape[1]} x {habitual.shape[0]} px, "
      f"lagunas habituales ~{habitual.sum() * px_km2:.0f} km² (ventana con margen), "
      f"{config.AGUA_HABITUAL_TIF.stat().st_size / 1e3:.0f} KB")
