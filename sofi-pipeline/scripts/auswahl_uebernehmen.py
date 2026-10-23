"""Übernimmt die Bildauswahl von der Auswahlseite nach sofi-pipeline/bilder/auswahl.yaml.

  python sofi-pipeline/scripts/auswahl_uebernehmen.py <ordner-mit-json>

Der Ordner enthält die Dokumente der Collection `auswahl`, wie sie das ArtifactData-Tool mit
`out_dir` speichert (je Dokument eine JSON-Datei).
- Neue Seiten (noch nicht in auswahl.yaml): Wahl übernehmen.
- Bereits entschiedene Seiten: nur übernehmen, wenn die Wahl auf der Seite eine andere Datei ist UND
  jünger als `gewaehlt` des Eintrags (so überschreibt eine alte Wahl keine Änderung von Hand).
Nur Dateien aus der Kandidatenliste. Neue und geänderte Einträge mit Bild bekommen ein leeres `alt:`
(ein altes `fokus` fällt weg) – den Alt-Text schreibt die Session, nachdem sie das Bild angesehen hat.
Jeder Eintrag trägt `gewaehlt` (Zeitpunkt der Wahl). Gibt die neuen und geänderten Schlüssel aus.

Von Hand ändern (z. B. auf Wunsch im Chat): Eintrag anpassen und `gewaehlt` auf die aktuelle Zeit setzen
(`date -u +%Y-%m-%dT%H:%M:%SZ`).
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


def _eintrag(v) -> dict:
    return dict(v) if isinstance(v, dict) else {"datei": str(v)}


def schreiben(alle: dict, kopf: str) -> None:
    zeilen = []
    for s in sorted(alle, key=_reihenfolge):
        v = _eintrag(alle[s])
        z = f"{s}:\n  datei: {json.dumps(v['datei'], ensure_ascii=False)}\n"
        if v["datei"] != "kein":
            z += f"  alt: {json.dumps(v.get('alt') or '', ensure_ascii=False)}\n"
            if v.get("fokus"):
                z += f"  fokus: {json.dumps(v['fokus'])}\n"
        if v.get("gewaehlt"):
            z += f"  gewaehlt: {json.dumps(str(v['gewaehlt']))}\n"
        zeilen.append(z)
    AUSWAHL.write_text(kopf + "".join(zeilen))
    assert set(yaml.safe_load(AUSWAHL.read_text())) == set(alle)


def uebernehmen(ordner: Path) -> list[str]:
    k = json.loads(KANDIDATEN.read_text())
    erlaubt = {s: {c["datei"] for c in v["kandidaten"]} for s, v in k.items()}

    text = AUSWAHL.read_text() if AUSWAHL.exists() else ""
    kopf = "".join(z for z in text.splitlines(True) if z.startswith("#"))
    alle = {s: _eintrag(v) for s, v in (yaml.safe_load(text) or {}).items()}
    geaendert: list[str] = []
    for f in sorted(ordner.rglob("*.json")):
        d = json.loads(f.read_text())
        d = d.get("data", d)
        schluessel, datei, zeit = d.get("schluessel"), d.get("datei"), d.get("geaendert") or ""
        if not schluessel or schluessel not in erlaubt or not datei:
            continue
        if datei != "kein" and datei not in erlaubt[schluessel]:
            print(f"übersprungen (nicht in den Kandidaten): {schluessel} → {datei}", file=sys.stderr)
            continue
        alt = alle.get(schluessel)
        if alt is not None:
            if alt["datei"] == datei:
                alt.setdefault("gewaehlt", zeit)      # alte Einträge ohne Zeit nachtragen
                continue
            if zeit <= str(alt.get("gewaehlt") or ""):
                continue                              # Repo-Stand ist neuer (z. B. von Hand geändert)
        alle[schluessel] = {"datei": datei, "alt": "", "gewaehlt": zeit}
        geaendert.append(schluessel)
        print(("geändert: " if alt is not None else "neu: ") + f"{schluessel} → {datei}")

    if alle:
        schreiben(alle, kopf)
    return geaendert


if __name__ == "__main__":
    uebernehmen(Path(sys.argv[1]))
