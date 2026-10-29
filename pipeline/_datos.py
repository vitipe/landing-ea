"""Lectura y escritura de serie.json y quincenas.json, y fechas de las quincenas."""
import calendar
import json
from datetime import date, datetime, timedelta, timezone

import config


# --- Quincenas: 1 al 15 y 16 a fin de mes ----------------------------------------

def quincena(inicio):
    """(desde, hasta) de la quincena que empieza en `inicio` (día 1 o 16)."""
    if inicio.day not in (1, 16):
        raise SystemExit(f"{inicio}: una quincena empieza el día 1 o el 16")
    if inicio.day == 1:
        return inicio, inicio.replace(day=15)
    return inicio, inicio.replace(day=calendar.monthrange(inicio.year, inicio.month)[1])


def ultima_cerrada(hoy):
    """Inicio de la última quincena que ya terminó."""
    if hoy.day > 15:
        return hoy.replace(day=1)
    anterior = hoy.replace(day=1) - timedelta(days=1)
    return anterior.replace(day=16)


def quincenas_del_anio(anio, hasta=None):
    hasta = hasta or date.max
    for mes in range(1, 13):
        for dia in (1, 16):
            inicio = date(anio, mes, dia)
            if quincena(inicio)[1] < hasta:
                yield inicio


# --- serie.json: cifras por partido, arrays alineados con "quincenas" -------------

VARIABLES = ["agua_km2" if i == "mndwi" else i for i in config.INDICES] + ["agua_transitoria_km2", "valido_pct"]


def _leer(ruta, vacio):
    if not ruta.exists():
        return vacio
    with open(ruta) as f:
        return json.load(f)


def _escribir(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")


def leer_serie(ruta=None):
    """{quincena: {partido: fila}} a partir de serie.json."""
    s = _leer(ruta or config.SERIE_JSON, {"quincenas": []})
    filas = {}
    for i, q in enumerate(s["quincenas"]):
        filas[q] = {p: {v: s[v][p][i] for v in VARIABLES if v in s and p in s[v]} for p in s["partidos"]}
    return filas


def escribir_serie(filas, partidos, ruta=None, demo=False):
    qs = sorted(filas)
    s = {"demo": demo, "partidos": partidos, "quincenas": qs}
    for v in VARIABLES:
        s[v] = {p: [filas[q].get(p, {}).get(v) for q in qs] for p in partidos}
    _escribir(ruta or config.SERIE_JSON, s)


# --- quincenas.json: qué quincenas tienen rásters en el sitio ---------------------

def leer_quincenas():
    return _leer(config.QUINCENAS_JSON, {"demo": False, "quincenas": []})


def registrar_quincena(entrada, demo=False):
    """Agrega o reemplaza la quincena y poda: quedan las QUINCENAS_PUBLICADAS más
    nuevas con rásters y las no publicadas posteriores a la más vieja de esas."""
    q = leer_quincenas()
    lista = [e for e in q["quincenas"] if e["id"] != entrada["id"]] + [entrada]
    lista.sort(key=lambda e: e["id"], reverse=True)
    publicadas = [e for e in lista if e["publicada"]][:config.QUINCENAS_PUBLICADAS]
    limite = publicadas[-1]["id"] if publicadas else ""
    lista = [e for e in lista if e in publicadas or (not e["publicada"] and e["id"] > limite)]
    datos = {
        "demo": demo,
        "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quincenas": lista,
    }
    _escribir(config.QUINCENAS_JSON, datos)
    return datos
