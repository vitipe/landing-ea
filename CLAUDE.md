# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Static landing site for NODOAGRO, a Buenos Aires agro consultancy (estudios agroeconómicos y particiones rurales), plus a satellite monitor at `/monitor/` (see below). All visible content is in Spanish (`lang="es-AR"`); keep new copy in Spanish. The owner deliberately uses "partición rural" rather than "subdivisión rural" — don't reintroduce "subdivisión".

The site's goals are ranking in Google for its services and getting visitors to make contact (WhatsApp is the primary channel).

## Commands

```bash
npm install          # once
npm run build        # compile Tailwind: src/input.css -> css/styles.css (minified)
npm run watch        # rebuild on change
python3 armar_sitio.py && python3 -m http.server 8000 -d _site   # preview at http://localhost:8000
```

Monitor pipeline (Python 3.14, `pip install -r pipeline/requirements.txt` in a venv):

```bash
python pipeline/00_demo_sintetico.py              # synthetic data for UI work (overwrites monitor/data/*.json; undo with git checkout monitor/data)
python pipeline/01_quincena.py                    # last closed fortnight (real Sentinel-2 data)
python pipeline/01_quincena.py --quincena 2026-09-16
python pipeline/02_historico.py --anio 2019       # past fortnights, stats only
```

There is no linter or test suite. Checks: `python3 -m py_compile pipeline/*.py armar_sitio.py`, `node --check monitor/app.js`.

## Architecture

- **All markup lives in `index.html`**, including SEO metadata and the JSON-LD block.
- **Tailwind v4 is compiled, not loaded from the CDN.** `src/input.css` scans only `index.html` (`source(none)` + `@source`). After adding or changing any Tailwind class, run `npm run build` and commit `css/styles.css` — GitHub Pages serves the repo as-is with no build step, so a stale `styles.css` means missing styles in production. Also bump the `?v=` on the stylesheet `<link>` (use the date, e.g. `?v=20261013`): Pages serves it with a 10-minute cache, so without a new URL returning visitors get new HTML with the old CSS and lose any newly added classes.
- **Deployment is GitHub Pages via Actions** (`.github/workflows/publicar.yml`, Settings → Pages → Source: GitHub Actions), custom domain `www.nodoagro.com.ar`. Pushing to `main` publishes the site. `armar_sitio.py` copies only the files listed in `PUBLICOS` into `_site/` (README, CLAUDE.md, `pipeline/` and Node files stay private), so a new public root file (e.g. a Search Console verification file) must be added there. Tailwind is still not built in CI: keep committing `css/styles.css`.
- **Images**: the hero is an `<img>` inside a `<picture>` (WebP at 800w/1600w with the JPG as fallback). `og:image`/`twitter:image` use a separate 1200×630 crop, `images/og-nodoagro.jpg`, kept under ~300 KB because WhatsApp may drop the link preview for heavier images. The nav uses the 96px `nodoagro_logo-96.png`; the 400px original is kept for JSON-LD. If the hero photo changes, regenerate the WebP variants and the OG crop.

## Keeping duplicated data consistent

Business facts are repeated across several places; when changing one, update all of them:

- Title/description: `<title>`, `meta description`, `og:*`, `twitter:*`, and the JSON-LD `description`.
- Contact info: JSON-LD (`telephone`, `contactPoint`, `email`), the `#contacto` section, the FAQ answer, and every `wa.me/5492929410181` link (hero CTA, service cards, contact card, floating button, `monitor/index.html`).
- Services: the service cards, the FAQ, and JSON-LD `hasOfferCatalog`.
- Hero image: the `<picture>` sources, plus `images/og-nodoagro.jpg` (`og:image`, `og:image:width/height`, `twitter:image`).
- Canonical URL / domain: `CNAME`, `<link rel="canonical">`, `og:url`, JSON-LD URLs, `robots.txt`, `sitemap.xml`, and the absolute URLs in `monitor/index.html`.
- Bump `<lastmod>` in `sitemap.xml` when page content changes meaningfully.

## Monitor satelital (`/monitor/`)

A fortnightly map of NDVI (vigor), MNDWI (surface water) and NDMI (vegetation moisture) for Guaminí and its neighbours (Adolfo Alsina, Coronel Suárez, Daireaux, Salliqueló, Trenque Lauquen, Tres Lomas). Its purpose is outreach: people check it every 15 days and see that NODOAGRO does particiones rurales.

- **Data source: Sentinel-2 L2A from Earth Search** (`sentinel-2-c1-l2a`, surface reflectance/BOA, Copernicus open data, fine for commercial use). `sentinel-2-c1-l2a` has big gaps (almost nothing in 2017 and Jan–Nov 2022, partial 2018, scattered passes missing elsewhere), so `_s2.buscar` also searches `sentinel-2-l2a` (`COLECCION_RESPALDO`) and keeps one item per MGRS tile and day, preferring C1 and then the newest processing baseline. Items whose assets aren't `https://` are skipped: part of `sentinel-2-l2a` (most of 2018) points to the requester-pays bucket `s3://sentinel-s2-l2a`, so 2018 stays partial. Older `sentinel-2-l2a` items have BOA offset 0 instead of −0.1, so `_s2.cubo` loads each calibration group separately and concatenates them on `time`. **Don't use Earth Engine** here: the owner's GEE project is registered as noncommercial, and promoting a business is commercial use. Same caution for basemaps: the map uses OSM tiles; Esri imagery would need an ArcGIS API key.
- **Flow:** `.github/workflows/monitor.yml` runs on days 3 and 18 → `pipeline/01_quincena.py` → COGs (uint8, `v = q/127 − 1`, 255 = no data, EPSG:3857) and an OG image in `salida/` → uploaded to the GitHub release `monitor-datos` (pruned to what `quincenas.json` lists) → `monitor/data/serie.json` and `quincenas.json` committed to `main` → calls `publicar.yml`, which downloads the release into `_site/monitor/data/cog/`. Rasters never go into git (they'd add ~1 GB/year; the Pages site limit is 1 GB). The workflow's commit also keeps the cron alive (GitHub disables schedules after 60 days without activity).
- **Publishing thresholds** (`pipeline/config.py`): a fortnight gets rasters only if ≥ `MIN_VALIDO_ZONA` of the zone has a cloud-free observation (SCL mask, dilated around clouds); a partido shows figures only if ≥ `MIN_VALIDO_PARTIDO` is cloud-free. Cloudy fortnights are recorded as `publicada: false` and the page says so.
- **Never publish demo data:** `00_demo_sintetico.py` writes `"demo": true`, the page shows a banner, and `armar_sitio.py --release` refuses to build. Don't commit demo JSON.
- `monitor/` doesn't use Tailwind (own `style.css`, layout taken from proyectos-geo). Bump the `?v=` on `style.css` and `app.js` when they change.
- `monitor/data/partidos.geojson` comes from the IGN WFS (`ign:departamento`, filtered by INDEC code `in1`, simplified to 50 m in EPSG:32720).
- `.github/workflows/historico.yml` (manual) backfills stats for past years so the chart can compare with previous years; one job per year.
- Rendering uses `geotiff.js` (range requests, picks the right overview) with a small `L.GridLayer` in `app.js`; no georaster-layer-for-leaflet (2 MB bundle).

Also keep consistent: the partidos list appears in `monitor/index.html` (subtitle and meta/OG descriptions), the landing's `#monitor` section and `partidos.geojson`; the monitor's WhatsApp link (`monitor/index.html`) counts as one of the `wa.me` links listed above.
