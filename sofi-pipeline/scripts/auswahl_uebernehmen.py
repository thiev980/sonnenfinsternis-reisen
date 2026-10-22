"""Übernimmt die Bildauswahl von der Auswahlseite nach sofi-pipeline/bilder/auswahl.yaml.

  python sofi-pipeline/scripts/auswahl_uebernehmen.py <ordner-mit-json>

Der Ordner enthält die Dokumente der Collection `auswahl`, wie sie das ArtifactData-Tool mit
`out_dir` speichert (je Dokument eine JSON-Datei). Übernommen werden nur Schlüssel, die in
auswahl.yaml noch fehlen, und nur Dateien aus der Kandidatenliste. Neue Einträge bekommen ein
leeres `alt:` – den Alt-Text schreibt die Session, nachdem sie das Bild angesehen hat.
Gibt die neu übernommenen Schlüssel aus.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from bilder import AUSWAHL, KANDIDATEN  # noqa: E402

REIHENFOLGE = ["seite", "sofi", "nordlicht", "guide"]


def _reihenfolge(k: str):
    art, _, slug = k.partition("/")
    return (REIHENFOLGE.index(art) if art in REIHENFOLGE else 9, slug)


def uebernehmen(ordner: Path) -> list[str]:
    k = json.loads(KANDIDATEN.read_text())
    erlaubt = {s: {c["datei"] for c in v["kandidaten"]} for s, v in k.items()}

    text = AUSWAHL.read_text() if AUSWAHL.exists() else ""
    vorhanden = yaml.safe_load(text) or {}
    neu: dict[str, str] = {}
    for f in sorted(ordner.rglob("*.json")):
        d = json.loads(f.read_text())
        d = d.get("data", d)
        schluessel, datei = d.get("schluessel"), d.get("datei")
        if not schluessel or schluessel in vorhanden or schluessel not in erlaubt:
            continue
        if datei != "kein" and datei not in erlaubt[schluessel]:
            print(f"übersprungen (nicht in den Kandidaten): {schluessel} → {datei}", file=sys.stderr)
            continue
        neu[schluessel] = datei

    if neu:
        kopf = "".join(z for z in text.splitlines(True) if z.startswith("#"))
        alle = {**vorhanden, **neu}
        zeilen = []
        for s in sorted(alle, key=_reihenfolge):
            v = alle[s]
            if isinstance(v, str):
                v = "kein" if v == "kein" else {"datei": v, "alt": ""}
            if v == "kein":
                zeilen.append(f"{s}: kein\n")
            else:
                zeilen.append(f"{s}:\n  datei: {json.dumps(v['datei'], ensure_ascii=False)}\n"
                              f"  alt: {json.dumps(v.get('alt', ''), ensure_ascii=False)}\n"
                              + (f"  fokus: {json.dumps(v['fokus'])}\n" if v.get("fokus") else ""))
        AUSWAHL.write_text(kopf + "".join(zeilen))
        assert set(yaml.safe_load(AUSWAHL.read_text())) == set(alle)
    for s in sorted(neu, key=_reihenfolge):
        print(s, "→", neu[s])
    return list(neu)


if __name__ == "__main__":
    uebernehmen(Path(sys.argv[1]))
