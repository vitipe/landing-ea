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
   and visit `http://localhost:8000`.

## Deployment

The site is served by GitHub Pages from `main` with the custom domain in `CNAME` (`www.nodoagro.com.ar`). Run `npm run build` and commit `css/styles.css` before pushing.
