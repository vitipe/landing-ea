# landing-ea

Landing website for an agro consultancy business built as a fast, responsive static site.

## Overview

This repository contains a single-page landing site for NODOAGRO, a consultancy focused on agroeconomic studies and rural partition services. The site includes:

- A hero section with a call-to-action
- Service presentation
- About section
- FAQ section
- Contact details (WhatsApp, phone and email links)
- Responsive navigation
- A satellite monitor at `/monitor/`: NDVI, surface water and vegetation moisture for Guaminí and neighbouring partidos, updated every 15 days from Sentinel-2

## Technologies

- HTML5
- Tailwind CSS v4 (compiled with the Tailwind CLI)
- Google Fonts (Montserrat)
- Static image assets

## Files

- `index.html` – main landing page markup
- `src/input.css` – Tailwind entry point and custom CSS
- `css/styles.css` – compiled CSS (generated, but committed because GitHub Pages has no build step)
- `images/` – image assets used in the site
- `monitor/` – monitor page (`index.html`, `app.js`, `style.css`) and its committed data (`data/*.json`, `data/partidos.geojson`)
- `pipeline/` – Python pipeline that computes each fortnight (`config.py` holds everything adjustable)
- `armar_sitio.py` – builds the publishable site into `_site/`
- `.github/workflows/` – `publicar.yml` (deploy), `monitor.yml` (every fortnight), `historico.yml` (one-off backfill)
- `favicon.ico`, `apple-touch-icon.png` – site icons

## Usage

1. Install dependencies once:
   ```bash
   npm install
   ```
2. Rebuild the CSS after changing classes in `index.html` or `src/input.css`:
   ```bash
   npm run build    # or: npm run watch
   ```
3. Preview locally:
   ```bash
   python3 -m http.server 8000
   ```
   and visit `http://localhost:8000`. To include the monitor as it will be published:
   ```bash
   python3 armar_sitio.py && python3 -m http.server 8000 -d _site
   ```

## Deployment

The site is deployed to GitHub Pages by `.github/workflows/publicar.yml` (Settings → Pages → Source: GitHub Actions) on every push to `main`, with the custom domain `www.nodoagro.com.ar`. Run `npm run build` and commit `css/styles.css` before pushing.

The monitor updates itself: `.github/workflows/monitor.yml` runs on the 3rd and 18th of each month, uploads the rasters to the `monitor-datos` release, commits `monitor/data/*.json` and redeploys. To run it by hand: Actions → Monitor satelital → Run workflow.
