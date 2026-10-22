# Headerbilder von Wikimedia Commons (astroreisen.com)

Übertragen von etappenunterkunft.de (`thiev980/etappen-pipeline`, `docs/BILDER.md`). Mensch wählt, Maschine
schlägt vor: Ein Workflow sucht Kandidaten, Thi wählt auf einer Auswahlseite, eine Claude-Session übernimmt die
Wahl samt Alt-Text, und der Workflow lädt die Bilder ins Repo.

## Grundsätze
- **Quelle:** nur Wikimedia Commons, nur CC0, Public Domain, CC BY, CC BY-SA. Bildzeile unter jedem Bild:
  «Foto: <Urheber>, <Lizenz mit Link>, via Wikimedia Commons (Link zur Dateiseite)».
- **Selbst gehostet:** Der Workflow lädt die Bilder nach `sofi-site/src/assets/bilder/`, Astro rechnet sie in
  WebP um (nur WebP, kein AVIF). Kein Abruf bei Wikimedia im Browser der Besucher.
- **Nie blockierend:** Seiten ohne gewähltes Bild sehen aus wie bisher (kein Platzhalter, kein `og:image`).
- **Alt-Texte von Hand**, Schweizer Rechtschreibung (ss): ein Satz, was zu sehen ist, mit Ortsnamen. Nichts
  behaupten, was nicht sichtbar oder durch den Dateinamen belegt ist. Wird auch als `og:image:alt` verwendet.

## Seiten und Schlüssel
| Schlüssel | Seite | Kandidaten |
|---|---|---|
| `sofi/<slug>` | Sonnenfinsternis-Ortsseite, **nur Orte mit Redaktionstext** | Wikidata-Bild (P18) + Commons-Geosuche 3 km |
| `nordlicht/<slug>` | Nordlicht-Ortsseite | wie oben + Commons-Suche «"<Ort>" aurora» |
| `guide/<slug>` | Guide (beide Bereiche) | Commons-Suche + Geosuche laut `bilder/seiten.yaml` |
| `seite/start`, `seite/sonnenfinsternis`, `seite/nordlichter` | Startseite, Übersichten | Commons-Suche laut `seiten.yaml` |

Platzierung: Ortsseiten und Guides unter Titel/Untertitel bzw. Datumszeile, vor dem Lead; Startseite und
Übersichten am Ende des Hero-Abschnitts. Format 21:9 (Handy 16:10), Bildausschnitt bei Bedarf über `fokus`.
Ranglisten, Karte, Methodik und Guide-Übersichten bekommen kein Headerbild.

## Dateien
| Datei | Zweck |
|---|---|
| `sofi-pipeline/scripts/bilder.py` | `kandidaten`, `vorschau`, `laden`; offline: `seiten` (Liste, ✓ = entschieden) |
| `sofi-pipeline/bilder/seiten.yaml` | Suchbegriffe für Übersichten/Guides, Ausnahmen für Orte (`radius`, `wikidata`) |
| `sofi-pipeline/bilder/kandidaten.json` | vom Workflow geschrieben; Seiten mit Kandidaten werden nicht neu gesucht |
| `sofi-pipeline/bilder/auswahl.yaml` | Schlüssel → `{datei, alt, fokus?}` oder `kein`; Push startet «Bilder aktualisieren» |
| `sofi-pipeline/scripts/auswahlseite.py` + `templates/auswahlseite.html` | baut die Auswahlseite |
| `sofi-pipeline/scripts/auswahl_uebernehmen.py` | Auswahl (ArtifactData-Export) → `auswahl.yaml`, neue Einträge mit leerem `alt:` |
| `.github/workflows/bilder.yml` | Kandidaten + Vorschauen (manuell, `inputs[kandidaten]=true`), Laden (Push auf `auswahl.yaml`) |
| `sofi-site/src/lib/bilder.ts`, `src/components/Headerbild.astro` | Bild + Bildzeile; `Base.astro` setzt `og:image` |

## Technische Hürden (Claude-Cloud-Session)
- Commons, Wikidata und upload.wikimedia.org sind aus der Session nicht erreichbar → alles im Workflow.
- Vorschaubilder liegen auf dem Branch `bilder-vorschau` (force-push), nicht auf main:
  `git clone --depth 1 -b bilder-vorschau https://github.com/thiev980/sonnenfinsternis-reisen /tmp/vorschau`.
  Dateiname = erste 16 Zeichen von SHA1 des Commons-Titels + `.jpg` (`bilder.vorschau_name`).
- Die Auswahlseite (claude.ai-Artifact) darf keine fremden Bilder laden → Vorschauen als data:-URIs.
- Workflows nur per REST starten (`gh api -X POST …/dispatches`); bei Anmeldefehlern vorher `unset GH_TOKEN`.

## Auswahlseite
URL: https://claude.ai/artifact/5uofzTt5VHGPKPTPg65p5R  ·  capabilities `{"db": {}}`, Collection `auswahl`,
Dokument-ID = Schlüssel mit `/` → `__`, Felder `schluessel`, `datei` (Commons-Titel oder `kein`).
Neu veröffentlichen: erst `Artifact action: read` mit der URL, dann `publish` mit `url` und `file_path`.

## Ablauf im Betrieb (in der geplanten Aufgabe «SoFi-Ortstexte (3 pro Tag)»)
**Schritt 0, jeden Lauf zuerst – Auswahl übernehmen:**
1. ArtifactData `list` auf die Collection `auswahl` der Auswahlseite, mit `out_dir` in einen leeren Ordner.
2. `python3 sofi-pipeline/scripts/auswahl_uebernehmen.py <ordner>` → neue Entscheidungen in `auswahl.yaml`.
3. Für jeden neuen Eintrag mit Bild das Vorschaubild (Branch `bilder-vorschau`) mit dem Read-Tool ansehen und
   `alt:` schreiben (Muster: bestehende Einträge). Bei Bildern, deren Motiv im 21:9-Zuschnitt angeschnitten
   würde, `fokus` setzen (z. B. `"50% 35%"`).
4. Committen und pushen («Bildauswahl übernommen: …»). Der Push startet «Bilder aktualisieren».

**Nach den neuen Texten – Kandidaten:**
1. Nach dem Push der Texte: `bilder.yml` mit `inputs[kandidaten]=true` starten, auf das Ende warten, `git pull`.
2. Vorschauen klonen, `python3 sofi-pipeline/scripts/auswahlseite.py <vorschau> <ausgabe.html>`, Auswahlseite
   neu veröffentlichen (siehe oben).
3. Telegram an Thi (Workflow `telegram-nachricht.yml` in `thiev980/affiliate-pipeline`), nur wenn neue Seiten
   zur Wahl stehen: «Astroreisen: Headerbilder wählen für <Orte> – <URL>».
