#!/usr/bin/env python3
"""
Berechnet die Geometrie der Totalitaetszone vom 2. August 2027 als GeoJSON:
Nordgrenze, Suedgrenze, Zentrallinie (Naeherung: Mitte zwischen den Grenzen)
fuer den Laengenbereich 12W bis 45E (Atlantik vor Cadiz bis Arabien).

Methode: pro Laengengrad-Spalte Binaersuche ueber die Breite auf die Kante
"Totalitaet ja/nein" (min. Separation < R_mond - R_sonne im Zeitfenster um
den lokalen Schattendurchgang). Praezision ~0.01 Grad (~1 km); die reale
Kante hat wegen des Mond-Limb-Profils ohnehin ~1-2 km Unschaerfe -> auf der
Website als Hinweis ausweisen ("an der Kante zaehlt jeder Kilometer").

Output: data/pfad.geojson
"""

import json
import numpy as np
from pathlib import Path

from skyfield.api import load, load_file, wgs84
from skyfield_data import get_skyfield_data_path

R_SUN_KM = 696_000.0
R_MOON_KM = 0.272281 * 6378.137
DATE = (2027, 8, 2)

LON_START, LON_END, LON_STEP = -12.0, 45.0, 0.5
LAT_MIN, LAT_MAX = 18.0, 40.0
EDGE_PRECISION = 0.01          # Grad Breite (~1.1 km)
WINDOW_MIN = 25                # +/- Minuten um den geschaetzten Durchgang
TIME_STEP_S = 10.0

BASE = Path(__file__).resolve().parent.parent

# Anker (lon, UTC-Dezimalstunden des Maximums) aus eclipse_raw.json-Orten
ANCHORS = [(-12.0, 8.72), (-6.29, 8.781), (-0.635, 8.894), (10.76, 9.194),
           (20.07, 9.516), (25.52, 9.756), (31.89, 10.045), (34.89, 10.181),
           (39.86, 10.447), (45.0, 10.62)]

ts = load.timescale(builtin=True)
eph = load_file(str(Path(get_skyfield_data_path()) / "de421.bsp"))
earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]


def transit_hour(lon):
    xs, ys = zip(*ANCHORS)
    return float(np.interp(lon, xs, ys))


def has_totality(lat, lon):
    """True, wenn der Punkt im Zeitfenster Totalitaet erlebt."""
    h = transit_hour(lon)
    n = int(2 * WINDOW_MIN * 60 / TIME_STEP_S) + 1
    hours = np.linspace(h - WINDOW_MIN / 60, h + WINDOW_MIN / 60, n)
    t = ts.utc(*DATE, hours)
    a = (earth + wgs84.latlon(lat, lon)).at(t)
    s = a.observe(sun).apparent()
    m = a.observe(moon).apparent()
    sep = s.separation_from(m).radians
    r_s = np.arcsin(R_SUN_KM / s.distance().km)
    r_m = np.arcsin(R_MOON_KM / m.distance().km)
    return bool(np.min(sep - (r_m - r_s)) < 0)


def edge(lat_inside, lat_outside, lon):
    """Binaersuche auf die Kante zwischen einem inneren und aeusseren Punkt."""
    while abs(lat_outside - lat_inside) > EDGE_PRECISION:
        mid = 0.5 * (lat_inside + lat_outside)
        if has_totality(mid, lon):
            lat_inside = mid
        else:
            lat_outside = mid
    return 0.5 * (lat_inside + lat_outside)


def column_limits(lon, prev=None):
    """Nord-/Suedgrenze fuer eine Laengengrad-Spalte."""
    if prev:
        n_prev, s_prev = prev
        center = 0.5 * (n_prev + s_prev)
        if has_totality(center, lon):
            inside = center
        else:
            prev = None  # Bracket verloren -> Vollscan
    if not prev:
        inside = None
        for lat in np.arange(LAT_MAX, LAT_MIN, -0.5):
            if has_totality(lat, lon):
                inside = float(lat)
                break
        if inside is None:
            return None
    # nach aussen laufende Startpunkte fuer die Suche
    hi = inside
    while hi < LAT_MAX and has_totality(hi + 0.5, lon):
        hi += 0.5
    lo = inside
    while lo > LAT_MIN and has_totality(lo - 0.5, lon):
        lo -= 0.5
    north = edge(hi, hi + 0.5, lon)
    south = edge(lo, lo - 0.5, lon)
    return north, south


def main():
    lons = np.arange(LON_START, LON_END + 1e-9, LON_STEP)
    north_pts, south_pts, center_pts = [], [], []
    prev = None
    for lon in lons:
        res = column_limits(float(lon), prev)
        if res is None:
            prev = None
            continue
        n, s = res
        prev = (n, s)
        north_pts.append([round(float(lon), 2), round(n, 3)])
        south_pts.append([round(float(lon), 2), round(s, 3)])
        center_pts.append([round(float(lon), 2), round(0.5 * (n + s), 3)])
        print(f"lon {lon:6.1f}  Süd {s:6.3f}  Nord {n:6.3f}  Breite {abs(n-s)*111:5.0f} km")

    def line(coords):
        return [[c[0], c[1]] for c in coords]

    zone_ring = line(north_pts) + line(south_pts)[::-1] + [line(north_pts)[0]]

    geo = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature",
             "properties": {"name": "Totalitätszone 2.8.2027"},
             "geometry": {"type": "Polygon", "coordinates": [zone_ring]}},
            {"type": "Feature",
             "properties": {"name": "Zentrallinie"},
             "geometry": {"type": "LineString", "coordinates": line(center_pts)}},
            {"type": "Feature",
             "properties": {"name": "Nordgrenze"},
             "geometry": {"type": "LineString", "coordinates": line(north_pts)}},
            {"type": "Feature",
             "properties": {"name": "Südgrenze"},
             "geometry": {"type": "LineString", "coordinates": line(south_pts)}},
        ],
    }
    dest = BASE / "data" / "pfad.geojson"
    dest.write_text(json.dumps(geo))
    print(f"\n→ {dest} ({len(center_pts)} Stützpunkte)")


if __name__ == "__main__":
    main()
