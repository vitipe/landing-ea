"""Arma el sitio publicable en _site/ (lo mismo que hace .github/workflows/publicar.yml).

Uso:
    python3 armar_sitio.py              # rásters del monitor desde salida/ (pipeline local o demo)
    python3 armar_sitio.py --release    # rásters desde el release monitor-datos (CI; necesita gh)
    python3 -m http.server 8000 -d _site     # http://localhost:8000 y /monitor/

Solo se publica lo que está en PUBLICOS: README, CLAUDE.md, el pipeline y los
archivos de Node quedan afuera. Un archivo nuevo en la raíz (por ejemplo, la
verificación de Search Console) hay que sumarlo a la lista.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SITIO = RAIZ / "_site"
PUBLICOS = ["index.html", "css", "images", "favicon.ico", "apple-touch-icon.png",
            "robots.txt", "sitemap.xml", "CNAME", "monitor"]
DATOS = RAIZ / "monitor" / "data"
RELEASE = "monitor-datos"        # el mismo que config.RELEASE del pipeline

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--release", action="store_true", help="bajar los rásters del release (modo CI)")
args = p.parse_args()

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
if args.release:
    r = subprocess.run(["gh", "release", "download", RELEASE, "--dir", str(cog), "--clobber"])
    if r.returncode != 0:
        print(f"Aviso: no se pudo bajar el release {RELEASE}; el monitor queda sin rásters")
elif (RAIZ / "salida").exists():
    for f in (RAIZ / "salida").iterdir():
        if f.suffix in (".tif", ".jpg"):
            shutil.copy2(f, cog / f.name)

# data/og-monitor.jpg: la imagen de la quincena publicada más nueva (o la de la landing)
og = next((q["og"] for q in quincenas.get("quincenas", []) if q.get("publicada") and q.get("og")), None)
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

tam = sum(f.stat().st_size for f in SITIO.rglob("*") if f.is_file()) / 1e6
print(f"Sitio armado en {SITIO} ({tam:.0f} MB; el límite de GitHub Pages es 1 GB)")
