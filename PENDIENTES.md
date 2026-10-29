# Pendientes del sitio NODOAGRO

Última actualización: 29 de octubre de 2026

## 1. Verificar ya (5 minutos)

- [ ] **WhatsApp:** desde un celular, tocar el botón verde flotante y confirmar que abre el chat con el **2929-410181** y el mensaje ya escrito.
- [ ] **Segundo teléfono:** tocar el **2923-409096** en la sección Contacto y confirmar que llama bien. Está cargado como celular (`+54 9 2923 409096`). Si es un fijo, hay que sacarle el 9 en `index.html`: en el enlace `tel:` y en los datos estructurados (JSON-LD).
- [ ] **Preguntas frecuentes:** leer las 5 respuestas y confirmar que sean correctas, sobre todo "¿Por qué el estudio agroeconómico es el primer paso de una partición rural?".

## 2. Google (lo que más pesa para aparecer en búsquedas)

- [ ] **Google Business Profile** (ficha en Google Maps): crearla en https://business.google.com
  - Categoría: algo como "Consultor agrícola" o "Servicio de consultoría".
  - Marcarla como empresa que atiende en una zona, sin dirección pública, y cargar los partidos donde trabajan.
  - Cargar web, teléfono, horario, logo y fotos de trabajos a campo.
  - Pedir reseñas a clientes conformes: es lo que más ayuda en búsquedas locales.
- [ ] **Google Search Console:** dar de alta el sitio en https://search.google.com/search-console
  - Verificar la propiedad. Si eligen el método de etiqueta HTML o de archivo, pasarle el código a Claude para que lo agregue al sitio.
  - Enviar el sitemap: `https://www.nodoagro.com.ar/sitemap.xml`
  - Con "Inspección de URLs", pedir que se indexe la página de inicio.
  - Revisar cada tanto el informe "Rendimiento": muestra con qué búsquedas aparecen y en qué posición.

## 3. Contenido que tienen que aportar ustedes

- [ ] **Equipo:** nombres, títulos, número de matrícula, foto y años de experiencia, para la sección "Un Equipo Interdisciplinario". Genera confianza y Google lo valora en servicios profesionales.
- [ ] **Zonas de trabajo:** lista de partidos donde hacen trabajos. Hoy el sitio solo dice "Casbas" y "Provincia de Buenos Aires".
- [ ] **Página propia para cada servicio** (`/estudio-agroeconomico/` y `/particion-rural/`). Para cada una hace falta:
  - qué es y cuándo se necesita
  - qué documentación tiene que traer el cliente
  - cómo es el proceso, paso a paso
  - plazos aproximados
- [ ] **Ejemplos de trabajos** (sin datos de clientes): tipo de campo, zona, qué se resolvió. Si hay mapas o imágenes SIG que se puedan mostrar, mejor.
- [ ] **Más preguntas frecuentes:** las consultas que más les hacen por teléfono o WhatsApp suelen ser las mismas que la gente busca en Google.

## 4. Monitor satelital (`/monitor/`)

- [x] **Publicación por Actions** activada (Settings → Pages → Source: GitHub Actions), con el dominio `www.nodoagro.com.ar` (28/10/2026).
- [x] **Primera corrida:** la 1.ª quincena de octubre vino nublada; se publicó la 2.ª de septiembre de 2026.
- [x] **Histórico 2017–2026** cargado (224 quincenas). 2018 queda parcial: parte de sus imágenes está en un bucket pago de AWS.
- [x] **Primera quincena revisada:** las Encadenadas (Del Monte, Cochicó, Alsina, Del Venado, Epecuén) aparecen como agua y no hay sombras de nubes.
- [x] **Alertas de sequía y exceso hídrico** por partido, en el panel y en la pestaña *Alertas* (29/10/2026).
- [ ] **Compartir el enlace** `https://www.nodoagro.com.ar/monitor/` en grupos de WhatsApp: la vista previa muestra el mapa de la última quincena. Para abrir directo en las alertas: `https://www.nodoagro.com.ar/monitor/#alertas`.
- Si una quincena viene nublada, el monitor lo avisa y muestra la anterior: no hay que hacer nada.
- Si hay que recalcular el histórico (por ejemplo, después de corregir el cálculo): Actions → *Histórico del monitor* → *Run workflow* con "Reemplazar las quincenas que ya están" tildado.

## 5. Medición (opcional)

- [ ] Crear una cuenta de **Google Analytics 4** y pasarle el ID (`G-XXXXXXX`) a Claude para que lo agregue al sitio y cuente los clics en WhatsApp, teléfono y email.

## 6. Mantenimiento

- **Si cambian textos:** editar `index.html`, hacer commit y push a `main`. Se publica solo en alrededor de un minuto.
- **Si agregan o cambian clases de Tailwind:** correr `npm run build` antes del commit; si no, esos estilos no se ven en el sitio publicado. Además, cambiar el número de `css/styles.css?v=...` en `index.html` (poner la fecha del día), para que los navegadores no sigan usando el CSS viejo.
- **El monitor se actualiza solo** los días 3 y 18 de cada mes. Si falla, GitHub manda un email; se puede volver a correr desde Actions.
- **Si el contenido cambia bastante:** actualizar la fecha `<lastmod>` en `sitemap.xml`.
- **En enero:** actualizar el año del pie de página (`© 2026`).
- **Si cambian un teléfono o el email:** está repetido en varios lugares; la lista completa está en `CLAUDE.md`.
