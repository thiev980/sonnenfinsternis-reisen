#!/usr/bin/env python3
"""
Baut das finale data/orte.json fuer die Website:
eclipse_raw.json (Astro) + cloud_stats.json (ERA5, falls vorhanden)
+ abgeleitete Felder (Ranking, SoFi-Score).

SoFi-Score = Totalitaetsdauer in Minuten x P(klarer Himmel).
Erwartungswert an "erlebten Totalitaets-Minuten" - die eine Zahl,
die den ganzen Vergleichsartikel traegt.
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"


def main():
    places = json.loads((DATA / "eclipse_raw.json").read_text())

    cloud_file = DATA / "cloud_stats.json"
    clouds = json.loads(cloud_file.read_text()) if cloud_file.exists() else {}
    if not clouds:
        print("Hinweis: cloud_stats.json fehlt noch - Wolkenfelder bleiben null.")
        print("         (scripts/cloud_era5.py download && aggregate)")

    for p in places:
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


if __name__ == "__main__":
    main()
