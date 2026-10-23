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
Übersichten am Ende des Hero-Abschnitts. Format 21:9 (Handy 16:10), Bildausschnitt über `fokus` (Standard `50% 62%`, `STANDARD_FOKUS` in `lib/bilder.ts`
und `zuschnitt.py`); `og:image` (1200×630) folgt grob demselben Fokus (oben/Mitte/unten).
Ranglisten, Karte, Methodik und Guide-Übersichten bekommen kein Headerbild.

## Dateien
| Datei | Zweck |
|---|---|
| `sofi-pipeline/scripts/bilder.py` | `kandidaten`, `vorschau`, `laden`; offline: `seiten` (Liste, ✓ = entschieden) |
| `sofi-pipeline/bilder/seiten.yaml` | Suchbegriffe für Übersichten/Guides (`suche`, `orte`, `anzahl` Kandidaten), Ausnahmen für Orte (`radius`, `wikidata`) |
| `sofi-pipeline/bilder/kandidaten.json` | vom Workflow geschrieben; Seiten mit Kandidaten werden nicht neu gesucht |
| `sofi-pipeline/bilder/auswahl.yaml` | Schlüssel → `{datei, alt, fokus?}` oder `kein`; Push startet «Bilder aktualisieren» |
| `sofi-pipeline/scripts/auswahlseite.py` + `templates/auswahlseite.html` | baut die Auswahlseite |
| `sofi-pipeline/scripts/zuschnitt.py` | Bogen mit Desktop-/Handy-Zuschnitt der gewählten Bilder, zum Setzen von `fokus` |
| `sofi-pipeline/scripts/auswahl_uebernehmen.py` | Auswahl (ArtifactData-Export) → `auswahl.yaml`, neue Einträge mit leerem `alt:` |
| `.github/workflows/bilder.yml` | Kandidaten + Vorschauen (manuell, `inputs[kandidaten]=true`), Laden (Push auf `auswahl.yaml`) |
| `sofi-site/src/lib/bilder.ts`, `src/components/Headerbild.astro` | Bild + Bildzeile; `Base.astro` setzt `og:image` |

## Technische Hürden (Claude-Cloud-Session)
- Commons, Wikidata und upload.wikimedia.org sind aus der Session nicht erreichbar → alles im Workflow.
- Vorschaubilder liegen auf dem Branch `bilder-vorschau` (force-push), nicht auf main:
  `git clone --depth 1 -b bilder-vorschau https://github.com/thiev980/sonnenfinsternis-reisen /tmp/vorschau`.
  Dateiname = erste 16 Zeichen von SHA1 des Commons-Titels + `.jpg` (`bilder.vorschau_name`).
- Die Auswahlseite (claude.ai-Artifact) darf keine fremden Bilder laden → Vorschauen als data:-URIs, aber nicht
  in der Seite selbst (Grenze 16 MB je Datei), sondern in mitveröffentlichten Skript-Dateien `vorschau/*.js`
  (je höchstens ~12 MB; ein Artifact darf 511 Dateien und 256 MB je Version haben → reicht für Tausende Bilder).
  `offen-N.js` lädt sofort, `gewaehlt-N.js` erst beim Aufklappen von «Bereits gewählt».
- Workflows nur per REST starten (`gh api -X POST …/dispatches`); bei Anmeldefehlern vorher `unset GH_TOKEN`.

## Auswahlseite
URL: https://claude.ai/artifact/5uofzTt5VHGPKPTPg65p5R  ·  capabilities `{"db": {}}`, Collection `auswahl`,
Dokument-ID = Schlüssel mit `/` → `__`, Felder `schluessel`, `datei` (Commons-Titel oder `kein`), `geaendert`.
Zeigt oben die offenen Seiten, darunter eingeklappt «Bereits gewählt» mit allen entschiedenen Seiten zum Umwählen.
Bauen: `python3 sofi-pipeline/scripts/auswahlseite.py <vorschau> <ausgabe-ordner>` → `index.html` + `vorschau/*.js`;
die letzte Ausgabezeile ist die JSON-Liste der Zusatzdateien.
Neu veröffentlichen: erst `Artifact action: read` mit der URL, dann `publish` mit `url`,
`file_path` = `<ausgabe-ordner>/index.html`, `root` = `<ausgabe-ordner>` und `files` = diese Liste
(capabilities weglassen, sie bleiben bestehen).

## Umwählen und Änderungen von Hand
- Auf der Auswahlseite unter «Bereits gewählt» ein anderes Bild (oder «Kein Bild») antippen → der nächste Lauf
  übernimmt es (`geändert: …` in der Ausgabe von `auswahl_uebernehmen.py`), schreibt einen neuen Alt-Text, und
  «Bilder aktualisieren» ersetzt das Bild.
- Jeder Eintrag in `auswahl.yaml` trägt `gewaehlt` (Zeitpunkt). Eine Wahl der Auswahlseite gilt nur, wenn sie
  jünger ist. Wer `auswahl.yaml` von Hand ändert (z. B. auf Wunsch im Chat), setzt `gewaehlt` auf jetzt
  (`date -u +%Y-%m-%dT%H:%M:%SZ`) – sonst nichts weiter.

## Ablauf im Betrieb (in der geplanten Aufgabe «SoFi-Ortstexte (3 pro Tag)»)
**Schritt 0, jeden Lauf zuerst – Auswahl übernehmen:**
1. ArtifactData `list` auf die Collection `auswahl` der Auswahlseite (`query.limit` 1000), mit `out_dir` in einen
   leeren Ordner.
2. `python3 sofi-pipeline/scripts/auswahl_uebernehmen.py <ordner>` → neue und geänderte Entscheidungen in
   `auswahl.yaml` (Ausgabe `neu: …` / `geändert: …`).
3. Für jeden neuen oder geänderten Eintrag mit Bild das Vorschaubild (Branch `bilder-vorschau`) mit dem Read-Tool
   ansehen und `alt:` schreiben (Muster: bestehende Einträge).
4. **Zuschnitt prüfen:** `python3 sofi-pipeline/scripts/zuschnitt.py <vorschau> <bogen.jpg> <schlüssel …>` und den
   Bogen mit dem Read-Tool ansehen (ganzes Bild mit Rahmen, daneben Desktop 21:9 und Handy 16:10). Standard ist
   `50% 62%` (etwas unter der Mitte). Ziel: Boden/Horizont mit Kontext (Bäume ganz, Häuser, Wasser), nicht nur
   Baumspitzen; Hauptmotiv (Turm, Korona, Polarlicht) nicht angeschnitten. Sonst `fokus` setzen («50% 80%» =
   mehr unten, «50% 35%» = mehr oben), erneut prüfen. Kein Kompromiss möglich (Hochformat-Motiv): in der
   Zusammenfassung erwähnen.
5. Committen und pushen («Bildauswahl übernommen: …»). Der Push startet «Bilder aktualisieren».

**Nach den neuen Texten – Kandidaten:**
1. Nach dem Push der Texte: `bilder.yml` mit `inputs[kandidaten]=true` starten, auf das Ende warten, `git pull`.
2. Vorschauen klonen, Auswahlseite bauen und neu veröffentlichen (siehe «Auswahlseite»).
3. Telegram an Thi (Workflow `telegram-nachricht.yml` in `thiev980/affiliate-pipeline`), nur wenn neue Seiten
   zur Wahl stehen: «Astroreisen: Headerbilder wählen für <Orte> – <URL>».

## Neue Kandidaten für eine Seite («noch eine Runde»)
1. Suchbegriffe in `seiten.yaml` anpassen (bei Bedarf `anzahl` erhöhen).
2. Den Schlüssel aus `kandidaten.json` und `auswahl.yaml` entfernen und das Dokument in der Collection `auswahl`
   löschen (ArtifactData `delete`, Dokument-ID mit `__`) – sonst übernimmt Schritt 0 die alte Wahl wieder.
3. `bilder.yml` mit `kandidaten=true` starten, Auswahlseite neu bauen und veröffentlichen.
