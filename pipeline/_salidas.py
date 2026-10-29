"""Salidas del monitor: cifras por partido, COG para la web e imagen para redes."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import rioxarray  # noqa: E402,F401  (registra el accessor .rio)
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from rasterio.enums import Resampling  # noqa: E402
from rasterio.features import rasterize  # noqa: E402
from rasterio.warp import reproject  # noqa: E402

import config  # noqa: E402

SIN_DATO = 255

# Misma rampa que PALETAS.ndvi en monitor/app.js
NDVI_PALETA = ["#a5673f", "#d9b26f", "#f2e394", "#a6d96a", "#4daf4a", "#1a7837", "#00441b"]
NDVI_RANGO = (-0.1, 0.9)


def etiquetas(partidos_calculo, geobox):
    """Ráster con 0 fuera de la zona e i + 1 dentro del partido i."""
    formas = [(g, i + 1) for i, g in enumerate(partidos_calculo.geometry)]
    return rasterize(formas, out_shape=geobox.shape, transform=geobox.affine, fill=0, dtype="int16")


def agua_habitual(geobox):
    """True donde hay laguna habitual (ver 03_agua_habitual.py), en la grilla de cálculo."""
    fraccion = np.zeros(geobox.shape, dtype="float32")
    with rasterio.open(config.AGUA_HABITUAL_TIF) as src:
        reproject(rasterio.band(src, 1), fraccion, dst_transform=geobox.affine, dst_crs=str(geobox.crs),
                  resampling=Resampling.average)
    return fraccion >= 0.5


def estadisticas(mediana, n_obs, etiq, nombres, habitual):
    """Cifras por partido y fracción de la zona con dato.

    Por partido: valido_pct siempre; y solo si el partido tiene al menos MIN_VALIDO_PARTIDO
    con dato, agua_km2 (MNDWI > umbral), agua_transitoria_km2 (la que está fuera de las
    lagunas habituales: campos anegados) y la media de los demás índices sobre tierra
    firme, sin el agua de la quincena ni las lagunas habituales (que si no tiran el
    promedio para abajo cuando crecen).
    """
    area_px = config.RESOLUCION_M ** 2
    con_dato = n_obs > 0
    with np.errstate(invalid="ignore"):
        agua = mediana["mndwi"] > config.UMBRAL_MNDWI
    filas = {}
    for i, nombre in enumerate(nombres, 1):
        en = etiq == i
        util = en & con_dato
        frac = util.sum() / max(en.sum(), 1)
        fila = {"valido_pct": int(round(100 * frac))}
        alcanza = frac >= config.MIN_VALIDO_PARTIDO
        tierra = util & ~agua & ~habitual
        for indice, valores in mediana.items():
            if indice == "mndwi":
                total = (util & agua).sum() * area_px / 1e6
                transitoria = (util & agua & ~habitual).sum() * area_px / 1e6
                fila["agua_km2"] = round(float(total), 1) if alcanza else None
                fila["agua_transitoria_km2"] = round(float(transitoria), 1) if alcanza else None
            else:
                fila[indice] = round(float(np.nanmean(valores[tierra])), 3) if alcanza and tierra.any() else None
        filas[nombre] = fila
    zona = etiq > 0
    valido_zona = float((zona & con_dato).sum() / max(zona.sum(), 1))
    return filas, valido_zona


def cuantizar(valores):
    """−1..1 a 0..254; 255 = sin dato. En la web: v = q / 127 − 1."""
    q = np.full(valores.shape, SIN_DATO, dtype="uint8")
    ok = np.isfinite(valores)
    q[ok] = np.clip(np.round((valores[ok] + 1) * 127), 0, 254).astype("uint8")
    return q


def guardar_cog(da, etiq, ruta):
    """Recorta a la zona, cuantiza, reproyecta a EPSG:3857 y guarda como COG."""
    q = da.copy(data=cuantizar(np.where(etiq > 0, da.values, np.nan)))
    q = q.rio.write_nodata(SIN_DATO)
    web = q.rio.reproject(config.CRS_WEB, resampling=Resampling.nearest, nodata=SIN_DATO)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    web.rio.to_raster(ruta, driver="COG", compress="DEFLATE", predictor="YES", level=9,
                      blocksize=512, overview_resampling="AVERAGE")
    return ruta


def imagen_og(ndvi, etiq, partidos_calculo, quincena, ruta):
    """JPG 1200×630 con el NDVI de la quincena, para la vista previa de WhatsApp."""
    paso = max(1, ndvi.shape[0] // 1000)
    v = np.where(etiq > 0, ndvi.values, np.nan)[::paso, ::paso]
    x = ndvi.x.values[::paso]
    y = ndvi.y.values[::paso]
    cmap = LinearSegmentedColormap.from_list("ndvi", NDVI_PALETA)
    cmap.set_bad("#f4f1ea")

    ancho, alto = config.ANCHO_OG / 100, config.ALTO_OG / 100
    fig = plt.figure(figsize=(ancho, alto), dpi=100, facecolor="#f4f1ea")
    ax = fig.add_axes([0.02, 0.03, 0.44, 0.94])
    ax.imshow(np.ma.masked_invalid(v), cmap=cmap, vmin=NDVI_RANGO[0], vmax=NDVI_RANGO[1],
              extent=[x[0], x[-1], y[-1], y[0]], interpolation="nearest")
    partidos_calculo.boundary.plot(ax=ax, color="#1d1d1b", linewidth=0.6)
    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(y[-1], y[0])
    ax.set_aspect("equal")
    ax.axis("off")

    izq = 0.50
    fig.text(izq, 0.83, "NODOAGRO", fontsize=18, fontweight="bold", color="#15803d")
    fig.text(izq, 0.71, "Monitor satelital de campos", fontsize=23, fontweight="bold", color="#1d1d1b")
    fig.text(izq, 0.60, "Vigor de la vegetación (NDVI)", fontsize=16, color="#1d1d1b")
    fig.text(izq, 0.53, quincena, fontsize=16, color="#1d1d1b")
    fig.text(izq, 0.45, "Guaminí y partidos vecinos · Sentinel-2", fontsize=12, color="#5f5e5a")
    barra = fig.add_axes([izq, 0.28, 0.42, 0.04])
    barra.imshow(np.linspace(*NDVI_RANGO, 256)[None, :], cmap=cmap, aspect="auto")
    barra.axis("off")
    fig.text(izq, 0.22, "Poco vigor", fontsize=11, color="#5f5e5a")
    fig.text(izq + 0.42, 0.22, "Mucho vigor", fontsize=11, color="#5f5e5a", ha="right")
    fig.text(izq, 0.08, "nodoagro.com.ar/monitor", fontsize=16, fontweight="bold", color="#15803d")

    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=100, facecolor=fig.get_facecolor(), pil_kwargs={"quality": 82, "optimize": True})
    plt.close(fig)
    return ruta
