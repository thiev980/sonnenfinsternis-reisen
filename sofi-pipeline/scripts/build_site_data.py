#!/usr/bin/env python3
"""
Baut das finale data/orte.json fuer die Website:
eclipse_raw.json (Astro) + cloud_stats.json (ERA5, falls vorhanden)
+ abgeleitete Felder (Ranking, SoFi-Score).

SoFi-Score = Totalitaetsdauer in Minuten x P(klarer Himmel).
Erwartungswert an "erlebten Totalitaets-Minuten" - die eine Zahl,
die den ganzen Vergleichsartikel traegt.

Die Kategorie wird hier aus den gerechneten Werten ABGELEITET (nicht in der
Ortsliste gepflegt), damit Label und Zahl nie auseinanderlaufen koennen.
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"

# Schwellen fuer die Kategorisierung. Beide liegen in einer echten Luecke der
# Daten, sind also nicht willkuerlich gesetzt:
#   Totalitaetsdauer: ... 74 s, 99 s, 111 s | 161 s, 173 s ...
#   Bedeckung ausserhalb der Zone: ... 98.4 % | 97.1 %, 94.8 % ...
KURZE_TOTALITAET_S = 120.0   # unter 2 Minuten = Randlage innerhalb der Zone
FAST_TOTAL_PCT = 98.0        # ab hier "knapp verpasst" statt "partiell"


def klassifiziere(p):
    """Leitet (category, rand_typ) aus den gerechneten Werten ab.

    category:
      "kern"     - Totalitaet von mindestens 2 Minuten
      "rand"     - Grenzfall, in beide Richtungen (siehe rand_typ)
      "partiell" - deutlich ausserhalb, reine Teilfinsternis

    rand_typ (nur bei category == "rand"):
      "knapp_innen"  - Totalitaet, aber unter 2 Minuten (Malaga, Jerez, Ronda)
      "knapp_aussen" - keine Totalitaet, aber >= 98 % Bedeckung (Hurghada, ...)
    """
    if p.get("is_total"):
        if p["totality_s"] < KURZE_TOTALITAET_S:
            return "rand", "knapp_innen"
        return "kern", None
    if p["obscuration_pct"] >= FAST_TOTAL_PCT:
        return "rand", "knapp_aussen"
    return "partiell", None


def main():
    places = json.loads((DATA / "eclipse_raw.json").read_text())

    cloud_file = DATA / "cloud_stats.json"
    clouds = json.loads(cloud_file.read_text()) if cloud_file.exists() else {}
    if not clouds:
        print("Hinweis: cloud_stats.json fehlt noch - Wolkenfelder bleiben null.")
        print("         (scripts/cloud_era5.py download && aggregate)")

    for p in places:
        p["category"], p["rand_typ"] = klassifiziere(p)

        c = clouds.get(p["slug"])
        p["cloud"] = c if c else None
        if p.get("is_total") and c:
            p["sofi_score"] = round(p["totality_s"] / 60.0 * c["p_clear"], 2)
        else:
            p["sofi_score"] = None

    # Ranking nur unter den Totalitaets-Orten
    total_places = [p for p in places if p.get("is_total")]
    for rank, p in enumerate(
        sorted(total_places, key=lambda x: -x["totality_s"]), start=1
    ):
        p["duration_rank"] = rank

    out = DATA / "orte.json"
    out.write_text(json.dumps(places, ensure_ascii=False, indent=2))
    n_cloud = sum(1 for p in places if p["cloud"])
    print(f"✓ {out}  ({len(places)} Orte, davon {len(total_places)} total, "
          f"{n_cloud} mit Wolkendaten)")
    for cat in ("kern", "rand", "partiell"):
        n = sum(1 for p in places if p["category"] == cat)
        print(f"    {cat:9s} {n:2d}")


if __name__ == "__main__":
    main()
