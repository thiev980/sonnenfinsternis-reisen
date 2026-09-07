"""
Geomagnetische Breite via Dipol-Naeherung (WMM2025-Referenz).

Praezision: +/- 1-2 Grad gegenueber dem vollen AACGM-Modell.
Fuer eine Reise-Entscheidungsebene ausreichend; die Vereinfachung
gehoert auf die Methodik-Seite, nicht versteckt.

Poldaten: NOAA/NCEI, WMM2025-Koeffizienten fuer Epoche 2025.0
Quelle: https://www.ncei.noaa.gov/products/wandering-geomagnetic-poles
Wandert um ca. 0.05-0.1 Grad/Jahr - Update-Turnus: alle paar Jahre pruefen,
nicht bei jedem Pipeline-Lauf.
"""
import math

# WMM2025, Epoche 2025.0, geozentrisch
GEOMAG_POLE_LAT = 80.79
GEOMAG_POLE_LON = -72.76


def geomag_latitude(lat: float, lon: float) -> float:
    """Geomagnetische Breite eines Ortes in Grad (Dipol-Naeherung)."""
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    pole_lat_r, pole_lon_r = math.radians(GEOMAG_POLE_LAT), math.radians(GEOMAG_POLE_LON)
    sin_val = (
        math.sin(lat_r) * math.sin(pole_lat_r)
        + math.cos(lat_r) * math.cos(pole_lat_r) * math.cos(lon_r - pole_lon_r)
    )
    return math.degrees(math.asin(sin_val))


if __name__ == "__main__":
    from nordlicht_orte_liste import ORTE

    print(f"{'Ort':<20} {'Land':<12} {'geogr. lat':>11} {'geomag. lat':>12}")
    for o in sorted(ORTE, key=lambda o: -geomag_latitude(o["lat"], o["lon"])):
        g = geomag_latitude(o["lat"], o["lon"])
        print(f"{o['name']:<20} {o['land']:<12} {o['lat']:>10.2f}° {g:>11.2f}°")
