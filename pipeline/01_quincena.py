"""Paso 1: índices de Sentinel-2 de una quincena para el monitor.

Uso (desde la raíz del repo):
    python pipeline/01_quincena.py                        # las quincenas cerradas que falten
    python pipeline/01_quincena.py --quincena 2026-09-16  # una en particular, aunque ya esté (día 1 o 16)

Sin --quincena procesa las cerradas posteriores a la más nueva de quincenas.json: si falló
una corrida, la siguiente la recupera. Si no falta ninguna, no hace nada.

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

if args.quincena:
    inicios = [args.quincena]
else:
    registradas = _datos.leer_quincenas()["quincenas"]    # de la más nueva a la más vieja
    ultima = date.fromisoformat(registradas[0]["id"]) if registradas else None
    inicios = _datos.pendientes(date.today(), ultima)
    if not inicios:
        raise SystemExit(f"No hay quincenas pendientes: la última cerrada ({ultima}) ya está registrada")

partidos = _quincena.leer_partidos()
for inicio in inicios:
    desde, hasta = _datos.quincena(inicio)
    if hasta >= date.today():
        raise SystemExit(f"La quincena {desde} termina el {hasta}: todavía no cerró")

    filas, entrada = _quincena.procesar(desde, hasta, partidos)

    serie = _datos.leer_serie()
    if filas:
        serie[desde.isoformat()] = filas
    _datos.escribir_serie(serie, list(partidos["nombre"]))   # siempre: la página necesita los JSON
    _alertas.escribir(serie, list(partidos["nombre"]))
    _datos.registrar_quincena(entrada)
    estado = "publicada" if entrada["publicada"] else f"sin rásters ({entrada.get('motivo')})"
    print(f"Quincena {desde} a {hasta}: {estado}")
