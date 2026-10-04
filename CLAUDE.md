# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Single-page static landing site for NODOAGRO, a Buenos Aires agro consultancy (estudios agroeconómicos y particiones rurales). All visible content is in Spanish (`lang="es-AR"`); keep new copy in Spanish. The owner deliberately uses "partición rural" rather than "subdivisión rural" — don't reintroduce "subdivisión".

The site's goals are ranking in Google for its services and getting visitors to make contact (WhatsApp is the primary channel).

## Commands

```bash
npm install          # once
npm run build        # compile Tailwind: src/input.css -> css/styles.css (minified)
npm run watch        # rebuild on change
python3 -m http.server 8000   # preview at http://localhost:8000
```

There is no linter or test suite.

## Architecture

- **All markup lives in `index.html`**, including SEO metadata and the JSON-LD block.
- **Tailwind v4 is compiled, not loaded from the CDN.** `src/input.css` scans only `index.html` (`source(none)` + `@source`). After adding or changing any Tailwind class, run `npm run build` and commit `css/styles.css` — GitHub Pages serves the repo as-is with no build step, so a stale `styles.css` means missing styles in production.
- **Deployment is GitHub Pages** from `main` with the custom domain in `CNAME` (`www.nodoagro.com.ar`). Pushing to `main` publishes the site.
- **Images**: the hero is an `<img>` inside a `<picture>` (WebP at 800w/1600w with the JPG as fallback). The JPG is also the `og:image`. The nav uses the 96px `nodoagro_logo-96.png`; the 400px original is kept for JSON-LD. If the hero photo changes, regenerate the WebP variants.

## Keeping duplicated data consistent

Business facts are repeated across several places; when changing one, update all of them:

- Title/description: `<title>`, `meta description`, `og:*`, `twitter:*`, and the JSON-LD `description`.
- Contact info: JSON-LD (`telephone`, `contactPoint`, `email`), the `#contacto` section, the FAQ answer, and every `wa.me/5492929410181` link (hero CTA, service cards, contact card, floating button).
- Services: the service cards, the FAQ, and JSON-LD `hasOfferCatalog`.
- Hero image: the `<picture>` sources plus `og:image` and `twitter:image`.
- Canonical URL / domain: `CNAME`, `<link rel="canonical">`, `og:url`, JSON-LD URLs, `robots.txt`, and `sitemap.xml`.
- Bump `<lastmod>` in `sitemap.xml` when page content changes meaningfully.
