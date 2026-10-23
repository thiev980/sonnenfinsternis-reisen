"""Baut die Auswahlseite für Headerbilder (claude.ai-Artifact mit Datenbank-Collection `auswahl`).

  python sofi-pipeline/scripts/auswahlseite.py <vorschau-ordner> <ausgabe-ordner>

Schreibt <ausgabe-ordner>/index.html (Seite mit allen Seiten und Kandidaten, ohne Bilder) und die
Vorschaubilder als Skript-Dateien <ausgabe-ordner>/vorschau/offen-N.js (offene Seiten, sofort geladen) und
vorschau/gewaehlt-N.js (entschiedene Seiten, erst beim Aufklappen von «Bereits gewählt» geladen).
Je Datei höchstens ~12 MB, damit die Grenzen eines Artifacts (16 MB je Datei, 256 MB je Version) auch bei
vielen Orten reichen. Gibt die Liste der Dateien für den `files`-Parameter als JSON aus.

Die Vorschaubilder kommen vom Branch `bilder-vorschau` (Workflow «Bilder aktualisieren» mit kandidaten=true):
`git clone --depth 1 -b bilder-vorschau https://github.com/thiev980/sonnenfinsternis-reisen <ordner>`.
Veröffentlichen: Artifact `publish` mit `url` https://claude.ai/artifact/5uofzTt5VHGPKPTPg65p5R,
`file_path` <ausgabe-ordner>/index.html, `files` = die ausgegebene Liste (`root` = <ausgabe-ordner>),
capabilities beim Republish weglassen (bleiben {"db": {}}).
Die Auswahl liegt in der Collection `auswahl`: Dokument-ID = Schlüssel mit «/» → «__»,
Felder `schluessel`, `datei` (Commons-Titel oder «kein»), `geaendert` (ISO-Zeit).
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from bilder import alle_gruppen, vorschau_name  # noqa: E402

VORLAGE = Path(__file__).parent / "templates" / "auswahlseite.html"
MAX_BYTES = 12_000_000


def _daten_uri(f: Path) -> str:
    im = Image.open(f).convert("RGB")
    im.thumbnail((380, 380))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=68, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def bauen(vorschau: Path, ausgabe: Path) -> list[str]:
    (ausgabe / "vorschau").mkdir(parents=True, exist_ok=True)
    for alt in (ausgabe / "vorschau").glob("*.js"):
        alt.unlink()
    gruppen, teile = [], {"offen": [{}], "gewaehlt": [{}]}
    groesse = {"offen": 0, "gewaehlt": 0}
    zuordnung: dict[str, str] = {}          # Bild-ID → Dateiname des Teils

    for g in alle_gruppen():
        art = "gewaehlt" if g["gewaehlt"] else "offen"
        gesehen, kand = set(), []
        for c in g["kand"]:
            h = vorschau_name(c["datei"])[:-4]
            f = vorschau / f"{h}.jpg"
            if c["datei"] in gesehen or not f.exists():
                continue
            gesehen.add(c["datei"])
            if h not in zuordnung:
                uri = _daten_uri(f)
                if groesse[art] + len(uri) > MAX_BYTES and teile[art][-1]:
                    teile[art].append({})
                    groesse[art] = 0
                teile[art][-1][h] = uri
                groesse[art] += len(uri)
                zuordnung[h] = f"{art}-{len(teile[art])}"
            a = c["autor"]
            kand.append({"datei": c["datei"], "bild": h, "quelle": c["quelle"], "lizenz": c["lizenz"],
                         "autor": a if len(a) <= 40 else a[:38].rstrip() + "…", "seite": c["seite"],
                         "q": c["wertung"]})
        gruppen.append({k: g[k] for k in ("key", "bereich", "titel", "gewaehlt", "seit")} | {"kand": kand})

    dateien, skripte = [], {"offen": [], "gewaehlt": []}
    for art, liste in teile.items():
        for i, bilder in enumerate(liste, 1):
            if not bilder:
                continue
            name = f"vorschau/{art}-{i}.js"
            inhalt = f"window.VORSCHAU=Object.assign(window.VORSCHAU||{{}},{json.dumps(bilder)});\n"
            (ausgabe / name).write_text(inhalt)
            v = hashlib.sha1(inhalt.encode()).hexdigest()[:10]
            skripte[art].append(f"{name}?v={v}")
            dateien.append(name)

    html = (VORLAGE.read_text()
            .replace("/*GRUPPEN*/[]", json.dumps(gruppen, ensure_ascii=False))
            .replace("/*SKRIPTE*/{}", json.dumps(skripte)))
    (ausgabe / "index.html").write_text(html)
    offen = sum(1 for g in gruppen if not g["gewaehlt"])
    mb = sum((ausgabe / d).stat().st_size for d in dateien) / 1e6
    print(f"{len(gruppen)} Seiten ({offen} offen), {len(zuordnung)} Bilder in {len(dateien)} Dateien "
          f"({mb:.1f} MB), Seite {len(html) / 1e3:.0f} KB → {ausgabe}", file=sys.stderr)
    print(json.dumps(dateien))
    return dateien


if __name__ == "__main__":
    bauen(Path(sys.argv[1]), Path(sys.argv[2]))
