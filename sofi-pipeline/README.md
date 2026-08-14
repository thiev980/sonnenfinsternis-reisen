# SoFi-2027-Daten-Pipeline

Daten-Grundstein für sonnenfinsternis-reisen.de: berechnet lokale Finsternis-Umstände
für 56 Orte entlang des Pfads vom 2. August 2027 und ergänzt sie um eine
ERA5-Wolkenklimatologie. Output ist ein statisches `orte.json`, aus dem
Ort-Seiten, Vergleichstabellen und die Leaflet-Karte generiert werden.

## Ablauf

```
pip install skyfield skyfield-data numpy          # Astro-Teil
python scripts/eclipse_calc.py                    # → data/eclipse_raw.json   (~30 s)

pip install cdsapi xarray netcdf4                 # Wolken-Teil (einmalig)
python scripts/cloud_era5.py download             # CDS-Account nötig, s.u.
python scripts/cloud_era5.py aggregate            # → data/cloud_stats.json + cloud_grid.json

python scripts/build_site_data.py                 # → data/orte.json (final)
```

`build_site_data.py` läuft auch ohne Wolkendaten (Felder bleiben dann `null`),
d.h. die Ort-Seiten können sofort gebaut und die Wolkendaten später
nachgeschoben werden.

## Wolkendaten: Copernicus CDS

1. Gratis-Account: https://cds.climate.copernicus.eu
2. API-Key nach CDS-Doku in `~/.cdsapirc`
3. Copernicus-Lizenz im Profil akzeptieren — sie erlaubt kommerzielle Nutzung,
   verlangt aber Attribution. Auf der Website in den Footer/Methodik-Teil:
   „Enthält modifizierte Copernicus Climate Change Service Informationen"
4. Download je nach CDS-Warteschlange Minuten bis Stunden — einmaliger Job.

Parameter: Total Cloud Cover, 1995–2024, 26.7.–9.8., 08–11 UTC (Finsternis-
Zeitfenster entlang des gesamten Pfads), 0.25°, Region 46N/12W–18N/46E.

## Validierung Astro-Teil (gegen NASA/Espenak-basierte Quellen)

| Ort       | Pipeline | publiziert |
|-----------|----------|------------|
| Tarifa    | 4m 39s   | 4m 39s     |
| Cádiz     | 2m 53s   | 2m 55s     |
| Gibraltar | 4m 27s   | 4m 27s     |
| Tanger    | 4m 50s   | 4m 51s     |
| Oran      | 5m 08s   | 5m 08s     |
| Sfax      | 5m 39s   | 5m 40s     |
| Bengasi   | 6m 09s   | 6m 09s     |
| Luxor     | 6m 20s   | 6m 20s     |
| Girga     | 6m 23s   | 6m 23s (globales Maximum) |
| Berlin    | 34.0 % partiell | „rund 34 %" |

Abweichungen ±1–2 s (kein Mond-Limb-Profil) — für Reise-Content irrelevant,
auf der Website trotzdem als „±wenige Sekunden" ausweisen, das ist zugleich
ein E-E-A-T-Signal (eigene Berechnung, Methodik offengelegt).

## Redaktionell wertvolle Befunde aus dem ersten Lauf

- **Sevilla (98.4 %), Hurghada (98.5 %), El Gouna (98.4 %), Kairo (94.8 %),
  Assuan (99.8 %) liegen NICHT in der Totalitätszone.** 99 % partiell ist
  qualitativ etwas völlig anderes als total — das ist der wichtigste
  Aufklärungs-Content überhaupt („Reicht Hurghada?" → Nein, Transfer nötig).
- **Lampedusa: 99.8 %, knapp außerhalb** — Euronews führt die Insel als „in
  der Totalitätszone". Möglicher Korrektur-/Faktencheck-Artikel (Randlage
  seriös darstellen, Pfadkanten-Unsicherheit erwähnen).
- **Málaga nur 1m 51s, Ronda 1m 14s, Jerez 1m 39s** — Randlagen mit stark
  verkürzter Totalität; „lohnt sich der Transfer nach Tarifa?"-Content.
- **Ceuta 4m 48s** — längste Totalität auf (politisch) spanischem Boden,
  kaum jemand auf dem Radar.
- Sonnenhöhe überall 37–82° → keine Horizont-Problematik wie 2026,
  aber Ägypten-Mittagssonne (81°) = Hitze-Thema für Guides.

## Dateien

- `scripts/eclipse_calc.py` — Astro-Berechnung (skyfield/DE421, Bisektion auf Kontakte)
- `scripts/cloud_era5.py` — ERA5-Download + Aggregation (Punkt-Stats + Karten-Grid)
- `scripts/build_site_data.py` — Merge + SoFi-Score (Dauer × P(klar)) + Ranking
- `data/eclipse_raw.json` — Astro-Rohdaten, 56 Orte
- `data/orte.json` — finales Site-Datenfile

## Nächste Ausbaustufen

1. ERA5-Lauf ausführen → SoFi-Score-Ranking wird scharf (Kernstück des
   „Wo ist die Chance am größten?"-Artikels)
2. Grid-Berechnung des Pfads (Zentrallinie + Nord-/Südgrenze als GeoJSON
   für Leaflet) — gleiches Skript-Muster, Raster statt Ortsliste
3. Astro/Hugo-Template, das pro Eintrag in orte.json eine Ort-Seite rendert
