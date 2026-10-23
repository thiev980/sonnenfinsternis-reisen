"""Zeigt, wie die gewählten Headerbilder auf der Seite zugeschnitten werden (zum Prüfen von `fokus`).

  python3 sofi-pipeline/scripts/zuschnitt.py <vorschau-ordner> <ausgabe.jpg> [schlüssel …]

Ohne Schlüssel: alle Einträge mit Bild aus auswahl.yaml. Je Zeile: ganzes Vorschaubild mit dem Ausschnitt
als Rahmen, daneben der Zuschnitt für Desktop (21:9) und Handy (16:10) – mit `fokus` des Eintrags oder dem
Standard (STANDARD_FOKUS, wie in Headerbild.astro). Vorschaubilder: Branch `bilder-vorschau`.
Das Ergebnis mit dem Read-Tool ansehen; wo Boden, Horizont oder das Motiv abgeschnitten wird, `fokus` in
auswahl.yaml setzen ("x% y%": 0% = oben/links behalten, 100% = unten/rechts behalten) und erneut prüfen.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from bilder import AUSWAHL, vorschau_name  # noqa: E402

STANDARD_FOKUS = "50% 62%"
H = 150


def _prozent(fokus: str) -> tuple[float, float]:
    x, _, y = (fokus or STANDARD_FOKUS).partition(" ")
    return float(x.rstrip("%")) / 100, float((y or "50%").rstrip("%")) / 100


def ausschnitt(w: int, h: int, verh: float, fokus: str) -> tuple[int, int, int, int]:
    """Wie CSS object-fit: cover mit object-position: Rechteck (l, o, r, u) im Bild."""
    fx, fy = _prozent(fokus)
    if w / h > verh:          # Bild breiter: links/rechts beschneiden
        cw, ch = round(h * verh), h
    else:                     # Bild höher: oben/unten beschneiden
        cw, ch = w, round(w / verh)
    l, o = round((w - cw) * fx), round((h - ch) * fy)
    return l, o, l + cw, o + ch


def bauen(vorschau: Path, ausgabe: Path, schluessel: list[str]) -> None:
    roh = yaml.safe_load(AUSWAHL.read_text()) or {}
    eintraege = [(k, v) for k, v in roh.items() if isinstance(v, dict) and v.get("datei") not in (None, "kein")
                 and (not schluessel or k in schluessel)]
    breite = round(H * 1.6) + round(H * 21 / 9) + round(H * 1.6) + 40
    bogen = Image.new("RGB", (breite, (H + 26) * len(eintraege)), "white")
    d = ImageDraw.Draw(bogen)
    for i, (k, v) in enumerate(eintraege):
        y0 = i * (H + 26)
        f = vorschau / vorschau_name(v["datei"])
        fokus = v.get("fokus") or STANDARD_FOKUS
        d.text((4, y0 + 4), f"{k}  ·  fokus {fokus}{'' if v.get('fokus') else ' (Standard)'}", fill="black")
        if not f.exists():
            d.text((4, y0 + 30), "Vorschaubild fehlt", fill="red")
            continue
        im = Image.open(f).convert("RGB")
        ganz = im.copy()
        ganz.thumbnail((round(H * 1.6), H))
        x = 0
        s = ganz.width / im.width
        rahmen = ImageDraw.Draw(ganz)
        r = ausschnitt(im.width, im.height, 21 / 9, fokus)
        rahmen.rectangle([round(c * s) for c in r], outline=(255, 200, 0), width=2)
        bogen.paste(ganz, (x, y0 + 22))
        x += round(H * 1.6) + 10
        for verh in (21 / 9, 16 / 10):
            teil = im.crop(ausschnitt(im.width, im.height, verh, fokus)).resize((round(H * verh), H))
            bogen.paste(teil, (x, y0 + 22))
            x += round(H * verh) + 10
    bogen.save(ausgabe, quality=82)
    print(f"{len(eintraege)} Bilder → {ausgabe}")


if __name__ == "__main__":
    bauen(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:])
