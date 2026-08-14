#!/usr/bin/env python3
"""
Wolkenklimatologie fuer den Finsternispfad 2027 aus ERA5-Reanalysedaten.

Laedt Total Cloud Cover (tcc) vom Copernicus Climate Data Store (CDS) fuer
26. Juli - 9. August, 08-11 UTC (Finsternis-Zeitfenster entlang des Pfads),
ueber 30 Jahre (1995-2024), Region Iberien bis Rotes Meer, 0.25 Grad.

Berechnet pro Ort (und optional als Grid fuer die Leaflet-Karte):
  - mean_tcc          mittlere Bewoelkung (0-1)
  - p_clear           P(tcc < 0.25)  "praktisch klar"
  - p_ok              P(tcc < 0.50)  "Sonne gut sichtbar"

VORAUSSETZUNGEN (einmalig, lokal):
  1. Gratis-Account auf https://cds.climate.copernicus.eu
  2. API-Key in ~/.cdsapirc hinterlegen (siehe CDS-Doku "API how to")
  3. pip install cdsapi xarray netcdf4 numpy
  4. Lizenz "Copernicus licence" im CDS-Profil akzeptieren
     (erlaubt kommerzielle Nutzung, verlangt nur Attribution:
      "Enthaelt modifizierte Copernicus Climate Change Service Informationen 2025")

LAUFZEIT: Download je nach CDS-Warteschlange Minuten bis Stunden (einmalig!),
Aggregation danach < 1 Minute. Datenmenge: grob 1-2 GB NetCDF.

Aufruf:  python cloud_era5.py download   # holt era5_tcc_*.nc
         python cloud_era5.py aggregate  # schreibt data/cloud_stats.json + cloud_grid.json
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "era5"
RAW.mkdir(parents=True, exist_ok=True)

YEARS = [str(y) for y in range(1995, 2025)]
HOURS = ["08:00", "09:00", "10:00", "11:00"]
# N, W, S, E  - Suedspanien bis Rotes Meer inkl. Puffer
AREA = [46, -12, 18, 46]
CLEAR_THRESHOLD = 0.25
OK_THRESHOLD = 0.50


def download():
    import cdsapi
    c = cdsapi.Client()
    jobs = [
        ("era5_tcc_jul.nc", "07", [str(d) for d in range(26, 32)]),
        ("era5_tcc_aug.nc", "08", [str(d) for d in range(1, 10)]),
    ]
    for fname, month, days in jobs:
        target = RAW / fname
        if target.exists():
            print(f"skip {fname} (existiert)")
            continue
        print(f"→ CDS-Request {fname} ...")
        c.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "variable": "total_cloud_cover",
                "year": YEARS,
                "month": month,
                "day": days,
                "time": HOURS,
                "area": AREA,
                "data_format": "netcdf",
                "download_format": "unarchived",
            },
            str(target),
        )
        print(f"  ✓ {target}")


def aggregate():
    import numpy as np
    import xarray as xr

    files = sorted(RAW.glob("era5_tcc_*.nc"))
    if not files:
        sys.exit("Keine NetCDF-Dateien gefunden - zuerst 'download' ausfuehren.")

    ds = xr.concat([xr.open_dataset(f) for f in files], dim="valid_time")
    tcc = ds["tcc"]  # dims: time, latitude, longitude

    mean_tcc = tcc.mean("valid_time")
    p_clear = (tcc < CLEAR_THRESHOLD).mean("valid_time")
    p_ok = (tcc < OK_THRESHOLD).mean("valid_time")

    # --- Grid-Export fuer die Leaflet-Choroplethe (abgespeckt auf 0.5 Grad) ---
    coarse = {
        "mean_tcc": mean_tcc.coarsen(latitude=2, longitude=2, boundary="trim").mean(),
        "p_clear": p_clear.coarsen(latitude=2, longitude=2, boundary="trim").mean(),
    }
    grid = {
        "lat": [round(float(v), 2) for v in coarse["mean_tcc"].latitude.values],
        "lon": [round(float(v), 2) for v in coarse["mean_tcc"].longitude.values],
        "mean_tcc": np.round(coarse["mean_tcc"].values, 3).tolist(),
        "p_clear": np.round(coarse["p_clear"].values, 3).tolist(),
        "meta": {
            "source": "ERA5 (C3S/ECMWF), 1995-2024, 26.7.-9.8., 08-11 UTC",
            "attribution": "Enthält modifizierte Copernicus Climate Change Service Informationen",
        },
    }
    (BASE / "data" / "cloud_grid.json").write_text(json.dumps(grid))
    print("✓ data/cloud_grid.json")

    # --- Punktwerte fuer die Ortsliste ---
    places = json.loads((BASE / "data" / "eclipse_raw.json").read_text())
    stats = {}
    for p in places:
        sel = dict(latitude=p["lat"], longitude=p["lon"], method="nearest")
        stats[p["slug"]] = {
            "mean_tcc": round(float(mean_tcc.sel(**sel)), 3),
            "p_clear": round(float(p_clear.sel(**sel)), 3),
            "p_ok": round(float(p_ok.sel(**sel)), 3),
        }
        print(f"{p['name']:24s} mean_tcc={stats[p['slug']]['mean_tcc']:.2f} "
              f"P(klar)={stats[p['slug']]['p_clear']:.0%}")

    (BASE / "data" / "cloud_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2))
    print("✓ data/cloud_stats.json")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "aggregate"
    {"download": download, "aggregate": aggregate}[cmd]()
