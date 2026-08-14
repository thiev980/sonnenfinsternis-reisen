# sonnenfinsternis-reisen.de — Astro-Site

Statische Website, generiert aus den Daten der SoFi-Pipeline (`orte.json`, `pfad.json`).

## Lokal arbeiten
```
npm install
npm run dev        # http://localhost:4321
npm run build      # → dist/
```

## Daten aktualisieren (z. B. nach dem ERA5-Lauf)
```
cp ../sofi-pipeline/data/orte.json    src/data/orte.json
cp ../sofi-pipeline/data/pfad.geojson src/data/pfad.json
npm run build
```
Alle 56 Ort-Seiten, Tabellen und die Karte ziehen sich automatisch aus diesen zwei Dateien.
Neuer Ort = neuer Eintrag in der Pipeline-Ortsliste, Pipeline laufen lassen, Dateien kopieren.

## Deployment (Cloudflare Pages)
1. GitHub-Repo anlegen, dieses Verzeichnis pushen
2. Cloudflare Dashboard → Workers & Pages → Create → Pages → Connect to Git
3. Build command: `npm run build` · Output directory: `dist`
4. Custom Domain: sonnenfinsternis-reisen.de verbinden (Nameserver auf Cloudflare)
5. Nach Livegang: Google Search Console → Property anlegen → Sitemap einreichen:
   `https://sonnenfinsternis-reisen.de/sitemap-index.xml`

## Vor dem Livegang (TODOs im Code markiert)
- [ ] Impressum ausfüllen (src/pages/impressum.astro)
- [ ] Datenschutz vervollständigen (src/pages/datenschutz.astro)
- [ ] Brevo-Formular-Action einsetzen (src/layouts/Base.astro, Suche nach "brevo-todo")

## Monetarisierungs-Slots (bereits im Template markiert)
- Ort-Seiten: `TODO Monetarisierung: Stay22` und `GetYourGuide` in src/pages/orte/[slug].astro
  → nach Programm-Freischaltung als Komponenten einsetzen, ein Edit wirkt auf alle 56 Seiten.
