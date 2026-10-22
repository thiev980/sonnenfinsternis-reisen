"""Baut die Auswahlseite für Headerbilder (claude.ai-Artifact mit Datenbank-Collection `auswahl`).

  python sofi-pipeline/scripts/auswahlseite.py <vorschau-ordner> <ausgabe.html>

Zeigt nur Seiten, die in sofi-pipeline/bilder/auswahl.yaml noch keine Entscheidung haben.
Die Vorschaubilder kommen vom Branch `bilder-vorschau` (Workflow «Bilder aktualisieren» mit
kandidaten=true): `git clone --depth 1 -b bilder-vorschau https://github.com/thiev980/sonnenfinsternis-reisen <ordner>`.
Sie werden verkleinert als data:-URIs eingebettet (die Artifact-Seite darf keine fremden Bilder laden).
Danach mit dem Artifact-Tool veröffentlichen (URL in docs/BILDER.md, capabilities {"db": {}}).
Die Auswahl liegt in der Collection `auswahl`: Dokument-ID = Schlüssel mit «/» → «__»,
Felder `schluessel`, `datei` (Commons-Titel oder «kein»).
"""
from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from bilder import offene_gruppen, vorschau_name  # noqa: E402

VORLAGE = Path(__file__).parent / "templates" / "auswahlseite.html"


def bauen(vorschau: Path, ausgabe: Path) -> int:
    bilder: dict[str, str] = {}

    def bild(titel: str) -> str | None:
        name = vorschau_name(titel)
        h = name[:-4]
        if h not in bilder:
            f = vorschau / name
            if not f.exists():
                return None
            im = Image.open(f).convert("RGB")
            im.thumbnail((380, 380))
            b = io.BytesIO()
            im.save(b, "JPEG", quality=68, optimize=True, progressive=True)
            bilder[h] = "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
        return h

    gruppen = []
    for g in offene_gruppen():
        gesehen, kand = set(), []
        for c in g["kand"]:
            b = bild(c["datei"])
            if not b or c["datei"] in gesehen:
                continue
            gesehen.add(c["datei"])
            a = c["autor"]
            kand.append({"datei": c["datei"], "bild": b, "quelle": c["quelle"], "lizenz": c["lizenz"],
                         "autor": a if len(a) <= 40 else a[:38].rstrip() + "…", "seite": c["seite"],
                         "q": c["wertung"]})
        gruppen.append(g | {"kand": kand})
    html = (VORLAGE.read_text()
            .replace("/*GRUPPEN*/[]", json.dumps(gruppen, ensure_ascii=False))
            .replace("/*BILDER*/{}", json.dumps(bilder)))
    ausgabe.write_text(html)
    print(f"{len(gruppen)} offene Seiten, {len(bilder)} Bilder, {len(html) / 1e6:.1f} MB → {ausgabe}")
    return len(gruppen)


if __name__ == "__main__":
    bauen(Path(sys.argv[1]), Path(sys.argv[2]))
