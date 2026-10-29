"""Paso 1: índices de Sentinel-2 de una quincena para el monitor.

Uso (desde la raíz del repo):
    python pipeline/01_quincena.py                        # última quincena cerrada
    python pipeline/01_quincena.py --quincena 2026-09-16  # una en particular (día 1 o 16)

Escribe los COG y la imagen para redes en salida/ y actualiza monitor/data/serie.json,
alertas.json y quincenas.json. En CI, monitor.yml sube salida/ al release y commitea los JSON.
Si la zona tiene menos de MIN_VALIDO_ZONA con dato (nubes), registra las cifras de los
partidos que se ven pero no publica rásters.
"""
import argparse
from datetime import date

import _alertas
import _datos
import _quincena

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--quincena", type=date.fromisoformat, help="Inicio de la quincena (AAAA-MM-01 o AAAA-MM-16)")
args = p.parse_args()

desde, hasta = _datos.quincena(args.quincena or _datos.ultima_cerrada(date.today()))
if hasta >= date.today():
    raise SystemExit(f"La quincena {desde} termina el {hasta}: todavía no cerró")

partidos = _quincena.leer_partidos()
filas, entrada = _quincena.procesar(desde, hasta, partidos)

serie = _datos.leer_serie()
if filas:
    serie[desde.isoformat()] = filas
_datos.escribir_serie(serie, list(partidos["nombre"]))   # siempre: la página necesita los JSON
_alertas.escribir(serie, list(partidos["nombre"]))
_datos.registrar_quincena(entrada)
estado = "publicada" if entrada["publicada"] else f"sin rásters ({entrada.get('motivo')})"
print(f"Quincena {desde} a {hasta}: {estado}")
