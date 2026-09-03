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
    # Kandidatenliste: (Name, Land, lat, lon) - grobe Auswahl zur Diskussion,
    # Koordinaten Stadtzentrum/bekannter Ausgangspunkt, nicht ueberpruefte Praezisionspunkte
    kandidaten = [
        ("Tromsø",        "Norwegen",  69.6517,  18.9556),
        ("Alta",          "Norwegen",  69.9689,  23.2717),
        ("Svolvær (Lofoten)", "Norwegen", 68.2340, 14.5687),
        ("Kiruna",        "Schweden",  67.8558,  20.2253),
        ("Abisko",        "Schweden",  68.3541,  18.7871),
        ("Rovaniemi",     "Finnland",  66.5039,  25.7294),
        ("Levi (Kittilä)", "Finnland", 67.8033,  24.8107),
        ("Saariselkä",    "Finnland",  68.4167,  27.4167),
        ("Reykjavik",     "Island",    64.1466, -21.9426),
        ("Akureyri",      "Island",    65.6885, -18.1262),
        ("Yellowknife",   "Kanada",    62.4540, -114.3718),
        ("Fairbanks",     "USA",       64.8378, -147.7164),
        ("Tórshavn",      "Färöer",    62.0107,  -6.7741),
        ("Aviemore",      "Schottland", 57.1930, -3.8270),
    ]

    print(f"{'Ort':<20} {'Land':<12} {'geogr. lat':>11} {'geomag. lat':>12}")
    for name, land, lat, lon in sorted(kandidaten, key=lambda k: -geomag_latitude(k[2], k[3])):
        print(f"{name:<20} {land:<12} {lat:>10.2f}° {geomag_latitude(lat, lon):>11.2f}°")
