"""Alerta temprana de sequía y exceso hídrico por partido, a partir de serie.json.

Cada valor se compara con la misma quincena de los demás años del registro (dejando
afuera el año evaluado: el registro es corto) y se expresa en desvíos (z):
    sequía: promedio de z(NDVI) y z(NDMI); negativo = más seco que lo normal
    exceso: z de log1p(agua_transitoria_km2), el agua fuera de las lagunas habituales
            (campos anegados, lagunas desbordadas); positivo = más agua que lo normal
Solo cuentan los partidos con al menos ALERTA_VALIDO_MIN % sin nubes.
Niveles: vigilancia y alerta según los umbrales de config.py. Una vigilancia que se
repite en la quincena anterior con dato (hasta un mes antes) sube a alerta, para no
alarmar por una sola imagen rara.
"""
import math
import statistics
from datetime import datetime, timezone

import _datos
import config

NIVELES = ["normal", "vigilancia", "alerta"]
MAX_SALTO = 2                    # quincenas entre una vigilancia y la anterior para que cuente como repetida


def _orden(q):
    """Quincenas desde el año 0: para medir saltos entre quincenas."""
    return int(q[:4]) * 24 + _posicion(q)


def _posicion(q):
    """0 a 23 dentro del año (como posicionEnAnio en monitor/app.js)."""
    return (int(q[5:7]) - 1) * 2 + (q[8:10] == "16")


def _valor(fila, variable):
    fila = fila or {}
    v = fila.get(variable)
    if v is None or (fila.get("valido_pct") or 0) < config.ALERTA_VALIDO_MIN:
        return None
    return math.log1p(v) if variable == "agua_transitoria_km2" else v


def _z(serie, q, partido, variable):
    """Desvíos respecto de la misma quincena en los demás años, o None si falta dato."""
    x = _valor(serie[q].get(partido), variable)
    if x is None:
        return None
    ref = [_valor(f.get(partido), variable) for otra, f in serie.items()
           if _posicion(otra) == _posicion(q) and otra[:4] != q[:4]]
    ref = [v for v in ref if v is not None]
    if len(ref) < config.ALERTA_ANIOS_MIN:
        return None
    desvio = max(statistics.stdev(ref), config.ALERTA_DESVIO_MIN[variable])
    return (x - statistics.fmean(ref)) / desvio


def _nivel(z, vigilancia, alerta):
    """Nivel por umbral; los umbrales negativos (sequía) se comparan al revés."""
    if z is None:
        return None
    signo = -1 if alerta < 0 else 1
    if z * signo >= alerta * signo:
        return "alerta"
    if z * signo >= vigilancia * signo:
        return "vigilancia"
    return "normal"


def calcular(serie, nombres):
    """{indicador: {partido: [(nivel, z) por quincena]}}, con las quincenas ordenadas."""
    qs = sorted(serie)
    umbrales = {"sequia": (config.SEQUIA_Z_VIGILANCIA, config.SEQUIA_Z_ALERTA),
                "exceso": (config.EXCESO_Z_VIGILANCIA, config.EXCESO_Z_ALERTA)}
    salida = {ind: {} for ind in umbrales}
    for p in nombres:
        z = {"exceso": [_z(serie, q, p, "agua_transitoria_km2") for q in qs]}
        transitoria = [(serie[q].get(p) or {}).get("agua_transitoria_km2") or 0 for q in qs]
        zn = [_z(serie, q, p, "ndvi") for q in qs]
        zm = [_z(serie, q, p, "ndmi") for q in qs]
        z["sequia"] = [None if a is None or b is None else (a + b) / 2 for a, b in zip(zn, zm)]
        for ind, (vig, ale) in umbrales.items():
            niveles = [_nivel(v, vig, ale) for v in z[ind]]
            if ind == "exceso":   # unos pocos km² sobre casi nada dan z enormes: no es exceso
                niveles = [n if n in (None, "normal") or km2 >= config.EXCESO_MIN_KM2 else "normal"
                           for n, km2 in zip(niveles, transitoria)]
            final, previo = [], None      # previo: (orden, nivel sin la regla de repetición)
            for q, nivel in zip(qs, niveles):
                if nivel is None:
                    final.append(None)
                    continue
                repetida = (previo and previo[1] != "normal" and _orden(q) - previo[0] <= MAX_SALTO)
                final.append("alerta" if nivel == "vigilancia" and repetida else nivel)
                previo = (_orden(q), nivel)
            salida[ind][p] = [(n, None if v is None else round(v, 2)) for n, v in zip(final, z[ind])]
    return qs, salida


def escribir(serie, nombres, demo=False):
    qs, salida = calcular(serie, nombres)
    datos = {
        "demo": demo,
        "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "anios": [qs[0][:4], qs[-1][:4]] if qs else [],
        "partidos": nombres,
        "quincenas": qs,
    }
    for ind, por_partido in salida.items():
        datos[f"{ind}_nivel"] = {p: [n for n, _ in v] for p, v in por_partido.items()}
        datos[f"{ind}_z"] = {p: [z for _, z in v] for p, v in por_partido.items()}
    _datos._escribir(config.ALERTAS_JSON, datos)
    return datos
