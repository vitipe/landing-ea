"""Configuración del monitor satelital (Sentinel-2, una corrida por quincena)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]      # raíz del repo

# --- Rutas ---------------------------------------------------------------------
MONITOR_DATA = RAIZ / "monitor" / "data"
PARTIDOS_GEOJSON = MONITOR_DATA / "partidos.geojson"   # IGN (ign:departamento), ver CLAUDE.md
SERIE_JSON = MONITOR_DATA / "serie.json"               # cifras por partido y quincena (se commitea)
QUINCENAS_JSON = MONITOR_DATA / "quincenas.json"       # quincenas publicadas y sus rásters (se commitea)
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
