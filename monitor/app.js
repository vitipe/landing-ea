// Monitor satelital. Lee data/quincenas.json, data/serie.json y data/partidos.geojson
// (los genera pipeline/01_quincena.py) y dibuja los COG de cada índice con geotiff.js,
// leyendo por range requests solo las teselas y el overview que hacen falta.

const SIN_DATO = 255; // en los COG: v = q / 127 − 1 (ver cuantizar() en pipeline/_salidas.py)

const INDICES = {
  ndvi: {
    nombre: "Vigor (NDVI)",
    variable: "ndvi",
    explica:
      "Cuánta vegetación verde y activa hay. El suelo desnudo o el rastrojo dan valores bajos; un cultivo o una pastura en pleno crecimiento, altos.",
    // Misma rampa que NDVI_PALETA en pipeline/_salidas.py
    paleta: ["#a5673f", "#d9b26f", "#f2e394", "#a6d96a", "#4daf4a", "#1a7837", "#00441b"],
    rango: [-0.1, 0.9],
    extremos: ["Poco vigor", "Mucho vigor"],
  },
  mndwi: {
    nombre: "Agua en superficie (MNDWI)",
    variable: "agua_km2",
    explica:
      "Lagunas, bajos y campos anegados: se marca en azul donde el MNDWI supera 0. El agua debajo de un cultivo o de un pastizal puede no verse.",
    umbral: 0,
    color: "#1d4e89",
  },
  ndmi: {
    nombre: "Humedad de la vegetación (NDMI)",
    variable: "ndmi",
    explica:
      "Cuánta agua tiene la vegetación. Valores bajos indican estrés hídrico o suelo seco; altos, vegetación bien provista de agua.",
    paleta: ["#8c510a", "#d8b365", "#f6e8c3", "#c7eae5", "#5ab4ac", "#01665e"],
    rango: [-0.3, 0.5],
    extremos: ["Seco", "Húmedo"],
  },
};

// Enlaces para compartir: /monitor/#agua abre directo en esa capa
const ANCLAS = { vigor: "ndvi", agua: "mndwi", humedad: "ndmi" };

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
  "septiembre", "octubre", "noviembre", "diciembre"];
const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

const $ = (id) => document.getElementById(id);
const fmtIndice = (v) => v.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtKm2 = (v) => `${Math.round(v).toLocaleString("es-AR")} km²`;
const fecha = (iso) => new Date(`${iso}T12:00:00`);
const nombreQuincena = (iso) => {
  const f = fecha(iso);
  return `${f.getDate() === 1 ? "1.ª" : "2.ª"} quincena de ${MESES[f.getMonth()]} de ${f.getFullYear()}`;
};
const posicionEnAnio = (iso) => {
  const f = fecha(iso);
  return f.getMonth() * 2 + (f.getDate() >= 16 ? 1 : 0);
};

async function cargar(nombre) {
  const r = await fetch(`data/${nombre}`);
  if (!r.ok) throw new Error(`No se pudo leer data/${nombre}`);
  return r.json();
}

// --- Colores --------------------------------------------------------------------

function hexARgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function colorEn(paleta, t) {
  const x = Math.min(Math.max(t, 0), 1) * (paleta.length - 1);
  const i = Math.min(Math.floor(x), paleta.length - 2);
  const a = hexARgb(paleta[i]);
  const b = hexARgb(paleta[i + 1]);
  return a.map((c, k) => Math.round(c + (b[k] - c) * (x - i)));
}

// RGBA para cada uno de los 256 valores posibles del COG
function tablaDeColores(cfg) {
  const tabla = new Uint8ClampedArray(256 * 4);
  for (let q = 0; q < SIN_DATO; q++) {
    const v = q / 127 - 1;
    let rgba = null;
    if (cfg.umbral !== undefined) {
      if (v > cfg.umbral) rgba = [...hexARgb(cfg.color), 255];
    } else {
      rgba = [...colorEn(cfg.paleta, (v - cfg.rango[0]) / (cfg.rango[1] - cfg.rango[0])), 255];
    }
    if (rgba) tabla.set(rgba, q * 4);
  }
  return tabla;
}

function leyenda(cfg) {
  if (cfg.umbral !== undefined) {
    return `<span><i style="background:${cfg.color}"></i>Agua (MNDWI mayor que ${cfg.umbral})</span>`;
  }
  const paradas = cfg.paleta.map((c, i) => `${c} ${(100 * i) / (cfg.paleta.length - 1)}%`).join(", ");
  return `<div class="barra" style="background:linear-gradient(to right, ${paradas})"></div>
    <div class="extremos"><span>${cfg.extremos[0]} (${fmtIndice(cfg.rango[0])})</span><span>${cfg.extremos[1]} (${fmtIndice(cfg.rango[1])})</span></div>`;
}

// --- Capa de teselas desde un COG en EPSG:3857 -----------------------------------

// allowFullFile: python -m http.server no responde range requests y manda el archivo
// entero; GitHub Pages sí (206), así que en el sitio publicado se lee por partes.
const tiffs = new Map();
function abrirTiff(url) {
  if (!tiffs.has(url)) tiffs.set(url, GeoTIFF.fromUrl(url, { allowFullFile: true }));
  return tiffs.get(url);
}

async function limitesCog(tiff) {
  const img = await tiff.getImage();
  const [x0, y0, x1, y1] = img.getBoundingBox();
  const sw = L.CRS.EPSG3857.unproject(L.point(x0, y0));
  const ne = L.CRS.EPSG3857.unproject(L.point(x1, y1));
  return L.latLngBounds(sw, ne);
}

const CapaCog = L.GridLayer.extend({
  initialize(tiff, tabla, opciones) {
    this._tiff = tiff;
    this._tabla = tabla;
    L.setOptions(this, opciones);
  },
  createTile(coords, listo) {
    const tesela = L.DomUtil.create("canvas", "capa-indice");
    const tam = this.getTileSize();
    tesela.width = tam.x;
    tesela.height = tam.y;
    const nw = coords.scaleBy(tam);
    const p0 = L.CRS.EPSG3857.project(this._map.unproject(nw, coords.z));
    const p1 = L.CRS.EPSG3857.project(this._map.unproject(nw.add(tam), coords.z));
    const bbox = [p0.x, p1.y, p1.x, p0.y];
    this._tiff
      .readRasters({ bbox, width: tam.x, height: tam.y, fillValue: SIN_DATO, resampleMethod: "nearest" })
      .then((bandas) => {
        const q = bandas[0];
        const ctx = tesela.getContext("2d");
        const imagen = ctx.createImageData(tam.x, tam.y);
        for (let i = 0; i < q.length; i++) {
          const j = q[i] * 4;
          imagen.data[i * 4] = this._tabla[j];
          imagen.data[i * 4 + 1] = this._tabla[j + 1];
          imagen.data[i * 4 + 2] = this._tabla[j + 2];
          imagen.data[i * 4 + 3] = this._tabla[j + 3];
        }
        ctx.putImageData(imagen, 0, 0);
        listo(null, tesela);
      })
      .catch((e) => listo(e, tesela));
    return tesela;
  },
});

async function valorEn(tiff, latlng) {
  const img = await tiff.getImage();
  const p = L.CRS.EPSG3857.project(latlng);
  const [ox, oy] = img.getOrigin();
  const [rx, ry] = img.getResolution();
  const col = Math.floor((p.x - ox) / rx);
  const fila = Math.floor((p.y - oy) / ry);
  if (col < 0 || fila < 0 || col >= img.getWidth() || fila >= img.getHeight()) return null;
  const [banda] = await img.readRasters({ window: [col, fila, col + 1, fila + 1] });
  return banda[0] === SIN_DATO ? null : banda[0] / 127 - 1;
}

// --- Página ---------------------------------------------------------------------

async function iniciar() {
  const [quincenas, serie, partidos] = await Promise.all([
    cargar("quincenas.json"), cargar("serie.json"), cargar("partidos.geojson"),
  ]);
  $("aviso-demo").hidden = !(quincenas.demo || serie.demo);

  const mapa = L.map("mapa", { zoomControl: true });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 16, attribution: "© OpenStreetMap",
  }).addTo(mapa);
  mapa.createPane("indice").style.zIndex = 350;

  const publicadas = quincenas.quincenas.filter((q) => q.publicada);
  const ultima = quincenas.quincenas[0];
  if (ultima && !ultima.publicada) {
    $("aviso").hidden = false;
    $("aviso").textContent = publicadas.length
      ? `La ${nombreQuincena(ultima.id)} vino muy nublada (${ultima.valido_pct}% de la zona sin nubes): mostramos la anterior.`
      : "Todavía no hay una quincena con suficientes imágenes despejadas.";
  }
  $("actualizado").textContent = textoActualizado(quincenas.actualizado);

  // Partidos
  const nombres = serie.partidos;
  let partidoSel = nombres.includes("Guaminí") ? "Guaminí" : nombres[0];
  const estilo = (f) => ({
    color: f.properties.nombre === partidoSel ? "#15803d" : "#1f2937",
    weight: f.properties.nombre === partidoSel ? 3 : 1.2,
    fill: true, fillOpacity: 0, interactive: true,
  });
  const capaPartidos = L.geoJSON(partidos, {
    style: estilo,
    onEachFeature: (f, capa) => {
      capa.bindTooltip(f.properties.nombre, { sticky: true });
      capa.on("click", () => elegirPartido(f.properties.nombre));
    },
  }).addTo(mapa);
  mapa.fitBounds(capaPartidos.getBounds());

  $("partido").innerHTML = nombres.map((n) => `<option>${n}</option>`).join("");
  $("partido").value = partidoSel;
  $("partido").addEventListener("change", () => elegirPartido($("partido").value));

  // Quincenas con rásters
  $("quincena").innerHTML = publicadas
    .map((q) => `<option value="${q.id}">${nombreQuincena(q.id)}</option>`).join("");
  let indiceSel = ANCLAS[location.hash.slice(1)] ?? "ndvi";
  let quincenaSel = publicadas[0]?.id;
  let capaIndice = null;
  let tiffSel = null;

  const grafico = new Chart($("grafico"), {
    type: "line",
    data: {
      labels: MESES_CORTOS.flatMap((m) => [`1.ª ${m}`, `2.ª ${m}`]),
      datasets: [],
    },
    options: {
      maintainAspectRatio: false,
      animation: false,
      spanGaps: true,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: { x: { ticks: { maxTicksLimit: 6, font: { size: 10 } } } },
    },
  });

  async function mostrarIndice() {
    const cfg = INDICES[indiceSel];
    document.querySelectorAll(".indices button").forEach((b) => {
      b.setAttribute("aria-pressed", b.dataset.indice === indiceSel);
    });
    $("explica").textContent = cfg.explica;
    $("leyenda").innerHTML = leyenda(cfg);
    if (capaIndice) mapa.removeLayer(capaIndice);
    capaIndice = null;
    const q = publicadas.find((x) => x.id === quincenaSel);
    if (!q) return;
    $("fechas").textContent = textoFechas(q);
    $("anio-copernicus").textContent = q.id.slice(0, 4);
    try {
      tiffSel = await abrirTiff(`data/${q.archivos[indiceSel]}`);
      capaIndice = new CapaCog(tiffSel, tablaDeColores(cfg), {
        pane: "indice", bounds: await limitesCog(tiffSel), opacity: 1 - $("opacidad").value / 100,
        tileSize: 256, maxZoom: 18,
      }).addTo(mapa);
    } catch (e) {
      $("aviso").hidden = false;
      $("aviso").textContent = "No se pudo cargar la capa de esta quincena. Probá de nuevo en un rato.";
      console.error(e);
    }
    mostrarPartido();
  }

  function elegirPartido(nombre) {
    partidoSel = nombre;
    $("partido").value = nombre;
    capaPartidos.setStyle(estilo);
    mostrarPartido();
  }

  function mostrarPartido() {
    const i = serie.quincenas.indexOf(quincenaSel);
    const dato = (v) => (i >= 0 ? serie[v]?.[partidoSel]?.[i] : null);
    const fila = (titulo, v, fmt) => `<dt>${titulo}</dt><dd>${v === null || v === undefined ? "sin dato" : fmt(v)}</dd>`;
    $("cifras").innerHTML =
      fila("Vigor medio (NDVI)", dato("ndvi"), fmtIndice) +
      fila("Agua en superficie", dato("agua_km2"), fmtKm2) +
      fila("Humedad media (NDMI)", dato("ndmi"), fmtIndice) +
      fila("Superficie sin nubes", dato("valido_pct"), (v) => `${v}%`);

    const cfg = INDICES[indiceSel];
    $("titulo-grafico").textContent = `${cfg.nombre}: ${partidoSel}`;
    const porAnio = {};
    serie.quincenas.forEach((q, k) => {
      const anio = Number(q.slice(0, 4));
      porAnio[anio] ??= Array(24).fill(null);
      porAnio[anio][posicionEnAnio(q)] = serie[cfg.variable]?.[partidoSel]?.[k] ?? null;
    });
    const anio = Number((quincenaSel ?? serie.quincenas.at(-1) ?? "").slice(0, 4));
    const anteriores = Object.keys(porAnio).map(Number).filter((a) => a < anio);
    const datasets = [];
    if (anteriores.length >= 2) {
      const promedio = Array.from({ length: 24 }, (_, k) => {
        const v = anteriores.map((a) => porAnio[a][k]).filter((x) => x !== null);
        return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null;
      });
      datasets.push({ label: `Promedio ${Math.min(...anteriores)}–${anio - 1}`, data: promedio,
        borderColor: "#9ca3af", borderDash: [4, 3], borderWidth: 1.5, pointRadius: 0 });
    }
    if (porAnio[anio - 1]) {
      datasets.push({ label: String(anio - 1), data: porAnio[anio - 1],
        borderColor: "#d9b26f", borderWidth: 1.5, pointRadius: 0 });
    }
    datasets.push({ label: String(anio), data: porAnio[anio] ?? [],
      borderColor: "#15803d", backgroundColor: "#15803d", borderWidth: 2.5, pointRadius: 2.5 });
    grafico.data.datasets = datasets;
    const esKm2 = cfg.variable === "agua_km2";
    grafico.options.scales.y = {
      title: { display: true, text: esKm2 ? "km²" : cfg.nombre.match(/\((.+)\)/)[1] },
      ticks: { callback: (v) => (esKm2 ? Math.round(v).toLocaleString("es-AR") : fmtIndice(v)) },
    };
    grafico.update();
    $("nota-grafico").textContent = anteriores.length >= 2
      ? "Compará esta quincena con el mismo momento de años anteriores."
      : "La comparación con años anteriores aparece cuando se carga el histórico.";
  }

  document.querySelectorAll(".indices button").forEach((b) => {
    b.addEventListener("click", () => {
      indiceSel = b.dataset.indice;
      const ancla = Object.keys(ANCLAS).find((k) => ANCLAS[k] === indiceSel);
      history.replaceState(null, "", `#${ancla}`);
      mostrarIndice();
    });
  });
  $("quincena").addEventListener("change", () => {
    quincenaSel = $("quincena").value;
    mostrarIndice();
  });
  $("opacidad").addEventListener("input", () => capaIndice?.setOpacity(1 - $("opacidad").value / 100));

  mapa.on("click", async (e) => {
    if (!tiffSel) return;
    const v = await valorEn(tiffSel, e.latlng);
    const cfg = INDICES[indiceSel];
    let texto = "Sin dato (nubes o fuera de la zona)";
    if (v !== null) {
      const sigla = indiceSel.toUpperCase();
      texto = cfg.umbral !== undefined
        ? `${sigla} ${fmtIndice(v)}: ${v > cfg.umbral ? "agua" : "sin agua en superficie"}`
        : `${sigla} ${fmtIndice(v)}`;
    }
    L.popup().setLatLng(e.latlng).setContent(texto).openOn(mapa);
  });

  $("seccion-partido").hidden = false;
  if (publicadas.length) {
    $("controles").hidden = false;
    await mostrarIndice();
  } else {
    mostrarPartido();
  }
}

function textoFechas(q) {
  const dias = q.escenas.map((d) => String(Number(d.slice(8, 10))));
  const mes = MESES[Number(q.id.slice(5, 7)) - 1];
  const lista = new Intl.ListFormat("es", { type: "conjunction" }).format(dias);
  const imagenes = dias.length === 1 ? `Imagen del ${lista}` : `Imágenes del ${lista}`;
  return `${imagenes} de ${mes} · ${q.valido_pct}% de la zona sin nubes`;
}

function textoActualizado(iso) {
  if (!iso) return "";
  const f = new Date(iso);
  const opciones = { day: "numeric", month: "long", timeZone: "America/Argentina/Buenos_Aires" };
  const proxima = new Date(f);
  proxima.setUTCDate(f.getUTCDate() + 1);
  while (![3, 18].includes(proxima.getUTCDate())) proxima.setUTCDate(proxima.getUTCDate() + 1);
  return `Actualizado el ${f.toLocaleDateString("es-AR", { ...opciones, year: "numeric" })} · ` +
    `próxima actualización alrededor del ${proxima.toLocaleDateString("es-AR", opciones)}.`;
}

iniciar().catch((e) => {
  $("aviso").hidden = false;
  $("aviso").textContent = "El monitor se está preparando: la primera actualización llega en los próximos días.";
  console.error(e);
});
