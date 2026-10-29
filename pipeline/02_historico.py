"""Paso 2: cifras de quincenas pasadas (sin rásters), para comparar con años anteriores.

Uso (desde la raíz del repo):
    python pipeline/02_historico.py --anio 2019                  # agrega 2019 a serie.json
    python pipeline/02_historico.py --anio 2019 --salida salida/serie_2019.json
    python pipeline/02_historico.py --unir salida/serie_*.json   # junta parciales en serie.json

Sentinel-2 L2A arranca a fines de 2015; con dos satélites (revisita de 5 días) desde 2017.
En CI, historico.yml corre un año por job y después los une. Cada quincena tarda
varios minutos, así que un año entero lleva un par de horas.
"""
import argparse
from datetime import date
from pathlib import Path

import _datos
import _quincena
import config

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--anio", type=int)
p.add_argument("--salida", type=Path, help="serie parcial (por defecto, monitor/data/serie.json)")
p.add_argument("--unir", type=Path, nargs="+", help="series parciales para sumar a serie.json")
p.add_argument("--pisar", action="store_true",
               help="con --unir, reemplaza las quincenas que ya estaban (después de corregir el cálculo)")
args = p.parse_args()

partidos = _quincena.leer_partidos()
nombres = list(partidos["nombre"])

def valido_medio(filas):
    """Promedio del % con dato de los partidos: para elegir entre dos cálculos de la misma quincena."""
    valores = [f.get("valido_pct") or 0 for f in filas.values()]
    return sum(valores) / max(len(valores), 1)


if args.unir:
    serie = _datos.leer_serie()
    for ruta in args.unir:
        parcial = _datos.leer_serie(ruta)
        # Una quincena que ya estaba solo se pisa si el cálculo nuevo tiene más dato
        # (por ejemplo, al sumar escenas de COLECCION_RESPALDO), o con --pisar
        nuevas = {q: f for q, f in parcial.items() if q not in serie}
        mejores = {q: f for q, f in parcial.items()
                   if q in serie and (args.pisar or valido_medio(f) > valido_medio(serie[q]))}
        serie.update(nuevas | mejores)
        print(f"{ruta.name}: {len(nuevas)} quincenas nuevas, {len(mejores)} mejoradas")
    _datos.escribir_serie(serie, nombres)
    raise SystemExit

if not args.anio:
    p.error("indicá --anio o --unir")

destino = args.salida or config.SERIE_JSON
serie = _datos.leer_serie(destino)
for inicio in _datos.quincenas_del_anio(args.anio, hasta=date.today()):
    if inicio.isoformat() in serie:
        continue
    filas, _ = _quincena.procesar(*_datos.quincena(inicio), partidos, rasters=False)
    if filas:
        serie[inicio.isoformat()] = filas
        _datos.escribir_serie(serie, nombres, destino)   # guarda a medida que avanza
print(f"{args.anio}: {sum(q.startswith(str(args.anio)) for q in serie)} quincenas en {destino}")
