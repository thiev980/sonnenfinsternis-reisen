"""
Gemeinsame Ortsliste fuer alle Nordlicht-Pipeline-Skripte.

Vorher stand diese Liste dreifach dupliziert in nordlicht_darkness.py,
nordlicht_cloud_era5.py und build_nordlicht_score.py - bei 11 statt 5
Orten zu riskant, weil ein Tippfehler in einer Kopie die Daten fuer einen
Ort unbemerkt verfaelschen wuerde. Jetzt: eine Liste, drei Importe.

Dictionaries statt Tupel, weil verschiedene Skripte unterschiedliche
Teilmengen der Felder brauchen (z.B. nordlicht_geomag.py braucht kein
utc_offset) - so kann sich kein Skript aus Versehen am falschen
Tupel-Index vergreifen.

utc_offset = Standardzeit (KEINE Sommerzeit), fuer die Nachtfenster-
Berechnung in nordlicht_cloud_era5.py.
"""

ORTE = [
    {"slug": "tromsoe",     "name": "Tromsø",      "land": "Norwegen", "lat": 69.6517,  "lon": 18.9556,   "utc_offset": 1},
    {"slug": "abisko",      "name": "Abisko",      "land": "Schweden", "lat": 68.3541,  "lon": 18.7871,   "utc_offset": 1},
    {"slug": "rovaniemi",   "name": "Rovaniemi",   "land": "Finnland", "lat": 66.5039,  "lon": 25.7294,   "utc_offset": 2},
    {"slug": "reykjavik",   "name": "Reykjavik",   "land": "Island",   "lat": 64.1466,  "lon": -21.9426,  "utc_offset": 0},
    {"slug": "yellowknife", "name": "Yellowknife", "land": "Kanada",   "lat": 62.4540,  "lon": -114.3718, "utc_offset": -7},
    # Erweiterung Runde 2 - Auswahl nach Bekanntheit, keine verifizierten
    # Suchvolumendaten (siehe Chat-Verlauf)
    {"slug": "akureyri",    "name": "Akureyri",    "land": "Island",   "lat": 65.6885,  "lon": -18.1262,  "utc_offset": 0},
    {"slug": "fairbanks",   "name": "Fairbanks",   "land": "USA",      "lat": 64.8378,  "lon": -147.7164, "utc_offset": -9},
    {"slug": "kiruna",      "name": "Kiruna",      "land": "Schweden", "lat": 67.8558,  "lon": 20.2253,   "utc_offset": 1},
    {"slug": "alta",        "name": "Alta",        "land": "Norwegen", "lat": 69.9689,  "lon": 23.2717,   "utc_offset": 1},
    {"slug": "saariselkae", "name": "Saariselkä",  "land": "Finnland", "lat": 68.4167,  "lon": 27.4167,   "utc_offset": 2},
    {"slug": "torshavn",    "name": "Tórshavn",    "land": "Färöer",   "lat": 62.0107,  "lon": -6.7741,   "utc_offset": 0},
]
