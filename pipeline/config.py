"""Configuración del monitor satelital (Sentinel-2, una corrida por quincena)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]      # raíz del repo

# --- Rutas ---------------------------------------------------------------------
MONITOR_DATA = RAIZ / "monitor" / "data"
PARTIDOS_GEOJSON = MONITOR_DATA / "partidos.geojson"   # IGN (ign:departamento), ver CLAUDE.md
SERIE_JSON = MONITOR_DATA / "serie.json"               # cifras por partido y quincena (se commitea)
QUINCENAS_JSON = MONITOR_DATA / "quincenas.json"       # quincenas publicadas y sus rásters (se commitea)
ALERTAS_JSON = MONITOR_DATA / "alertas.json"           # nivel de alerta por quincena y partido (se commitea)
AGUA_HABITUAL_TIF = RAIZ / "pipeline" / "datos" / "agua_habitual.tif"  # lagunas habituales (03_agua_habitual.py)

# --- Lagunas habituales: JRC Global Surface Water 1984-2024 (Copernicus, uso sin restricciones
# citando a Pekel et al. 2016). Separa el agua de las lagunas del agua en los campos.
JRC_OCURRENCIA_URL = ("https://storage.googleapis.com/water-world/download2024/VER1-5/occurrence/"
                      "occurrence_70W_30S_v1_5_2024.tif")
OCURRENCIA_HABITUAL = 50         # % de las observaciones 1984-2024 con agua: laguna habitual (como guamini-agua)
SALIDA = RAIZ / "salida"         # COG e imagen OG; en CI se suben al release, nunca a git
RELEASE = "monitor-datos"        # release de GitHub donde viven los rásters publicados

# --- Fuente --------------------------------------------------------------------
STAC_URL = "https://earth-search.aws.element84.com/v1"
COLECCION = "sentinel-2-c1-l2a"  # Nivel 2A: reflectancia de superficie (BOA), Collection 1
COLECCION_RESPALDO = "sentinel-2-l2a"  # completa las pasadas que faltan en COLECCION (tiene huecos
                                       # grandes en 2017, 2018 y 2022, y sueltos en otros años).
                                       # Mismos assets y scale/offset: el offset de BOA ya viene aplicado
NUBES_MAX_ESCENA = 95            # % de nubes de la tesela entera: solo descarta las tapadas del todo;
                                 # lo que decide es la máscara SCL píxel a píxel
SCL_VALIDAS = [4, 5, 6]          # vegetación, suelo desnudo, agua
DILATAR_NUBES_PX = 2             # agranda lo descartado por SCL: bordes de nubes que SCL no marca

# --- Grilla --------------------------------------------------------------------
CRS_CALCULO = "EPSG:32720"       # UTM 20S: las áreas salen en m²
CRS_WEB = "EPSG:3857"            # la del mapa web; los COG se reproyectan a esta
RESOLUCION_M = 30
CHUNK_PX = 2048

# --- Índices -------------------------------------------------------------------
# nombre -> (a, b): (a - b) / (a + b), con los nombres de asset de Earth Search
INDICES = {
    "ndvi": ("nir", "red"),        # B08, B04: vigor de la vegetación
    "mndwi": ("green", "swir16"),  # B03, B11: agua en superficie (el mismo de guamini-agua)
    "ndmi": ("nir08", "swir16"),   # B8A, B11: humedad de la vegetación (NDWI de Gao)
}
UMBRAL_MNDWI = 0.0               # MNDWI > umbral = agua

# --- Publicación ---------------------------------------------------------------
MIN_VALIDO_ZONA = 0.5            # fracción de la zona con dato para publicar los rásters
MIN_VALIDO_PARTIDO = 0.5         # fracción del partido con dato para mostrar sus cifras
QUINCENAS_PUBLICADAS = 4         # cuántas quincenas con rásters quedan en el sitio (límite de Pages: 1 GB)
ANCHO_OG = 1200                  # imagen para la vista previa de WhatsApp y redes
ALTO_OG = 630

# --- Alertas (ver _alertas.py) -------------------------------------------------
# z = desvíos respecto de la misma quincena en los demás años del registro.
# Calibrado con la serie 2017-2026: detecta la sequía de mar-ago 2023 en ~70% de los
# partidos-quincena y deja ~6% en alerta fuera de ella (incluye eventos reales como 2019 y 2025)
ALERTA_ANIOS_MIN = 5             # años de referencia con dato para calcular el nivel
ALERTA_VALIDO_MIN = 70          # % del partido sin nubes para calcular el nivel (más exigente que las cifras)
ALERTA_DESVIO_MIN = {"ndvi": 0.02, "ndmi": 0.02, "agua_transitoria_km2": 0.5}  # piso del desvío (agua: en log1p)
SEQUIA_Z_VIGILANCIA = -1.25      # promedio de z(NDVI) y z(NDMI)
SEQUIA_Z_ALERTA = -2.0
EXCESO_Z_VIGILANCIA = 1.25       # z de log1p(agua_transitoria_km2): agua fuera de las lagunas habituales
EXCESO_Z_ALERTA = 2.0
EXCESO_MIN_KM2 = 5               # menos agua fuera de lagunas que esto no alerta, aunque el z sea alto
