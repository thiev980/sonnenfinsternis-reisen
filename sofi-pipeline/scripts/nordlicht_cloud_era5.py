#!/usr/bin/env python3
"""
Wolkenklimatologie fuer Nordlicht-Zielorte aus ERA5-Reanalysedaten.

WICHTIGER UNTERSCHIED zu cloud_era5.py (Finsternis):
Die Finsternis-Orte liegen auf einer schmalen Ost-West-Linie und der
Kernschatten durchlaeuft sie alle am selben Vormittag - eine einzige feste
UTC-Stunde (08-11 UTC) und eine gemeinsame AREA-Box genuegen dort.

Die Nordlicht-Orte liegen von Kanada bis Skandinavien ueber fast den
halben Globus verteilt. "Nacht" ist an jedem Ort zu einer anderen
UTC-Stunde. Deshalb: pro Ort ein eigenes Nachtfenster (UTC-Stunden) UND
eine eigene, kleine Abfrageflaeche statt einer gemeinsamen Box.

Naeherung: Nachtfenster = 17:00-07:00 Ortszeit, STANDARDZEIT (keine
Sommerzeit-Korrektur). Das ist grosszuegig genug, um die tatsaechliche
astronomische Dunkelheit (siehe nordlicht_darkness.py) sicher einzuschliessen,
auch wenn die Grenzen nicht nacht-genau sind. Auf der Methodik-Seite
transparent machen, wie bei der geomagnetischen Naeherung.

VORAUSSETZUNGEN: wie cloud_era5.py (CDS-Account, API-Key, Lizenz akzeptiert).

LAUFZEIT: 35 einzelne CDS-Anfragen (5 Orte x 7 Monate) statt 2 bei der
Finsternis - realistisch Stunden statt Minuten Warteschlange. Erst mit
EINEM Ort testen (zweites Kommandozeilenargument), dann skalieren.

Aufruf:  python nordlicht_cloud_era5.py download [ort-slug]
         python nordlicht_cloud_era5.py aggregate
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "era5_nordlicht"
RAW.mkdir(parents=True, exist_ok=True)

YEARS = [str(y) for y in range(1995, 2025)]
MONTHS = ["09", "10", "11", "12", "01", "02", "03"]
CLEAR_THRESHOLD = 0.25
OK_THRESHOLD = 0.50

# Ortsliste: slug, name, lat, lon, UTC-Offset Standardzeit (ohne Sommerzeit)
LOCATIONS = [
    ("tromsoe",     "Tromsø",      69.6517,  18.9556,  1),
    ("abisko",      "Abisko",      68.3541,  18.7871,  1),
    ("rovaniemi",   "Rovaniemi",   66.5039,  25.7294,  2),
    ("reykjavik",   "Reykjavik",   64.1466, -21.9426,  0),
    ("yellowknife", "Yellowknife", 62.4540, -114.3718, -7),
]


def nacht_utc_stunden(utc_offset: int) -> list:
    """Nachtfenster 17:00-07:00 Ortszeit -> UTC-Stunden (wraps ueber Mitternacht)."""
    stunden = list(range(17, 24)) + list(range(0, 8))  # 17-06 lokal, 14h Fenster
    utc_stunden = sorted({(h - utc_offset) % 24 for h in stunden})
    return [f"{h:02d}:00" for h in utc_stunden]


def download(nur_ort=None):
    import cdsapi
    c = cdsapi.Client()

    for slug, name, lat, lon, offset in LOCATIONS:
        if nur_ort and slug != nur_ort:
            continue
        area = [round(lat + 0.5, 2), round(lon - 0.5, 2),
                round(lat - 0.5, 2), round(lon + 0.5, 2)]  # N, W, S, E
        hours = nacht_utc_stunden(offset)

        for month in MONTHS:
            fname = f"era5_tcc_{slug}_{month}.nc"
            target = RAW / fname
            if target.exists():
                print(f"skip {fname} (existiert)")
                continue
            print(f"→ CDS-Request {fname} (UTC-Stunden: {hours}) ...")
            c.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable": "total_cloud_cover",
                    "year": YEARS,
                    "month": month,
                    "day": [f"{d:02d}" for d in range(1, 29)],  # 28 - sicher fuer alle Monate
                    "time": hours,
                    "area": area,
                    "data_format": "netcdf",
                    "download_format": "unarchived",
                },
                str(target),
            )
            print(f"  ✓ {target}")


def aggregate():
    import numpy as np
    import xarray as xr

    monatsname = {
        "09": "sep", "10": "okt", "11": "nov", "12": "dez",
        "01": "jan", "02": "feb", "03": "mär",
    }

    ergebnis = {}
    for slug, name, lat, lon, offset in LOCATIONS:
        ergebnis[slug] = {"name": name}
        for month in MONTHS:
            f = RAW / f"era5_tcc_{slug}_{month}.nc"
            if not f.exists():
                print(f"⚠ fehlt: {f.name} - 'download' zuerst ausfuehren")
                continue
            ds = xr.open_dataset(f)
            tcc = ds["tcc"]
            sel = dict(latitude=lat, longitude=lon, method="nearest")
            werte = tcc.sel(**sel)

            m = monatsname[month]
            ergebnis[slug][m] = {
                "mean_tcc": round(float(werte.mean()), 3),
                "p_clear": round(float((werte < CLEAR_THRESHOLD).mean()), 3),
                "p_ok": round(float((werte < OK_THRESHOLD).mean()), 3),
            }
            print(f"{name:14s} {m}  P(klar)={ergebnis[slug][m]['p_clear']:.0%}")

    out = BASE / "data" / "cloud_stats_nordlicht.json"
    out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print(f"✓ {out}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "aggregate"
    ort_filter = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "download":
        download(nur_ort=ort_filter)
    else:
        aggregate()
