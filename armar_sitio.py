"""Arma el sitio publicable en _site/ (lo mismo que hace .github/workflows/publicar.yml).

Uso:
    npm run build                       # antes: compila css/styles.css
    python3 armar_sitio.py              # rásters del monitor desde salida/ (pipeline local o demo)
    python3 armar_sitio.py --release    # rásters desde el release monitor-datos (CI; necesita gh)
    python3 -m http.server 8000 -d _site     # http://localhost:8000 y /monitor/

Solo se publica lo que está en PUBLICOS: README, CLAUDE.md, el pipeline y los
archivos de Node quedan afuera. Un archivo nuevo en la raíz (por ejemplo, la
verificación de Search Console) hay que sumarlo a la lista.

En _site/ pone el ?v= de CSS y JS (hash del archivo) y el año del pie, y revisa las
páginas: si algo falla, corta y en CI queda online la publicación anterior.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SITIO = RAIZ / "_site"
PUBLICOS = ["index.html", "css", "images", "favicon.ico", "apple-touch-icon.png",
            "robots.txt", "sitemap.xml", "CNAME", "monitor"]
DATOS = RAIZ / "monitor" / "data"
RELEASE = "monitor-datos"        # el mismo que config.RELEASE del pipeline


def versionar(pagina, archivos):
    """?v= = hash de cada archivo: Pages cachea 10 minutos y sin esto el navegador
    combina HTML nuevo con CSS o JS viejos."""
    texto = pagina.read_text(encoding="utf-8")
    for nombre in archivos:
        huella = hashlib.sha256((pagina.parent / nombre).read_bytes()).hexdigest()[:10]
        texto, n = re.subn(re.escape(nombre) + r"\?v=[^\"']*", f"{nombre}?v={huella}", texto)
        if n != 1:
            sys.exit(f"{pagina.name}: esperaba un enlace a {nombre}?v=..., encontré {n}")
    pagina.write_text(texto, encoding="utf-8")


class Enlaces(HTMLParser):
    """Rutas de los atributos src, href y srcset de una página."""

    def __init__(self):
        super().__init__()
        self.rutas = []

    def handle_starttag(self, tag, attrs):
        for nombre, valor in attrs:
            if nombre in ("src", "href"):
                self.rutas.append(valor)
            elif nombre == "srcset":
                self.rutas += [parte.split()[0] for parte in valor.split(",") if parte.strip()]


def revisar(pagina):
    """Errores de una página armada: JSON-LD inválido, archivos locales que no están y
    "subdivisión" (el dueño usa "partición rural", ver CLAUDE.md)."""
    texto = pagina.read_text(encoding="utf-8")
    errores = []
    for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', texto, re.S):
        try:
            json.loads(bloque)
        except json.JSONDecodeError as e:
            errores.append(f"JSON-LD inválido: {e}")
    if re.search("subdivisi", texto, re.I):
        errores.append('aparece "subdivisión": usar "partición rural"')
    enlaces = Enlaces()
    enlaces.feed(texto)
    for ruta in enlaces.rutas:
        local = ruta.split("#")[0].split("?")[0]
        if not local or re.match(r"[a-z]+:", local):      # ancla, https:, mailto:, tel:
            continue
        destino = SITIO / local.lstrip("/") if local.startswith("/") else pagina.parent / local
        if destino.is_dir():
            destino = destino / "index.html"
        if not destino.exists():
            errores.append(f"enlace roto: {ruta}")
    return [f"{pagina.relative_to(SITIO)}: {e}" for e in errores]


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--release", action="store_true", help="bajar los rásters del release (modo CI)")
args = p.parse_args()

if not (RAIZ / "css" / "styles.css").exists():
    sys.exit("Falta css/styles.css: corré npm run build")

quincenas = {}
if (DATOS / "quincenas.json").exists():
    quincenas = json.loads((DATOS / "quincenas.json").read_text())
serie_demo = (DATOS / "serie.json").exists() and json.loads((DATOS / "serie.json").read_text()).get("demo")
if args.release and (quincenas.get("demo") or serie_demo):
    sys.exit("monitor/data tiene datos de demostración (demo: true). No se publican en nodoagro.com.ar: "
             "corré pipeline/01_quincena.py o borrá serie.json y quincenas.json.")

if SITIO.exists():
    shutil.rmtree(SITIO)
SITIO.mkdir()
for nombre in PUBLICOS:
    origen = RAIZ / nombre
    if origen.is_dir():
        shutil.copytree(origen, SITIO / nombre)
    elif origen.exists():
        shutil.copy2(origen, SITIO / nombre)

# Rásters e imágenes OG del monitor
cog = SITIO / "monitor" / "data" / "cog"
cog.mkdir(parents=True, exist_ok=True)
publicadas = [q for q in quincenas.get("quincenas", []) if q.get("publicada")]
if args.release:
    # Cortar acá deja online la publicación anterior, con sus capas
    if publicadas:
        r = subprocess.run(["gh", "release", "download", RELEASE, "--dir", str(cog), "--clobber"])
        if r.returncode != 0:
            sys.exit(f"No se pudo bajar el release {RELEASE}: no se publica, para no dejar el monitor sin capas.")
    faltan = [f for q in publicadas for f in [*q.get("archivos", {}).values(), q.get("og")]
              if f and not (SITIO / "monitor" / "data" / f).exists()]
    if faltan:
        sys.exit(f"quincenas.json nombra archivos que no están en el release {RELEASE}: {faltan}")
elif (RAIZ / "salida").exists():
    for f in (RAIZ / "salida").iterdir():
        if f.suffix in (".tif", ".jpg"):
            shutil.copy2(f, cog / f.name)

# data/og-monitor.jpg: la imagen de la quincena publicada más nueva (o la de la landing)
og = next((q["og"] for q in publicadas if q.get("og")), None)
origen_og = SITIO / "monitor" / "data" / og if og else None
if not (origen_og and origen_og.exists()):
    origen_og = RAIZ / "images" / "og-nodoagro.jpg"
shutil.copy2(origen_og, SITIO / "monitor" / "data" / "og-monitor.jpg")

# lastmod del monitor en el sitemap = última actualización
if quincenas.get("actualizado"):
    sitemap = SITIO / "sitemap.xml"
    texto = re.sub(r"(<loc>https://www\.nodoagro\.com\.ar/monitor/</loc>\s*<lastmod>)[^<]*",
                   rf"\g<1>{quincenas['actualizado'][:10]}", sitemap.read_text())
    sitemap.write_text(texto)

versionar(SITIO / "index.html", ["css/styles.css"])
versionar(SITIO / "monitor" / "index.html", ["style.css", "app.js"])

# Año del pie: el 3 de enero lo publica la corrida del monitor
portada = SITIO / "index.html"
texto, n = re.subn(r"&copy; \d{4}", f"&copy; {date.today().year}", portada.read_text(encoding="utf-8"))
if n != 1:
    sys.exit(f"index.html: esperaba un &copy; AAAA en el pie, encontré {n}")
portada.write_text(texto, encoding="utf-8")

errores = revisar(portada) + revisar(SITIO / "monitor" / "index.html")
if errores:
    sys.exit("Problemas en el sitio armado:\n  " + "\n  ".join(errores))

tam = sum(f.stat().st_size for f in SITIO.rglob("*") if f.is_file()) / 1e6
print(f"Sitio armado en {SITIO} ({tam:.0f} MB; el límite de GitHub Pages es 1 GB)")
