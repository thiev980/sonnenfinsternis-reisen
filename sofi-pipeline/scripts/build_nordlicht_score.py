"""
Merged geomagnetische Breite, Dunkelstunden und Wolkenklimatologie zu
data/nordlicht_orte.json - die Datei, die die Astro-Seiten konsumieren.

Index(Ort, Monat) = Dunkelstunden(Ort, Monat) x P(klar)(Ort, Monat)

Analog zum SoFi-Score (Totalitaetsminuten x P(klar)), aber pro Monat statt
einem einzelnen Datum, weil Nordlicht-Sichtbarkeit keine deterministische
Geometrie ist - siehe methodik.astro.

Geomagnetische Breite fliesst NICHT in den monatlichen Index ein, weil sie
sich nicht mit der Saison aendert. Sie steht als feste Ortseigenschaft
daneben und beantwortet "ist dieser Ort grundsaetzlich gut", nicht "wann".

Mondphase fliesst bewusst nicht ein - über 30 Jahre gemittelt hat jeder
Kalendermonat dieselbe mittlere Mondbeleuchtung, das waere reines Rauschen
in einer Klimatologie.

Voraussetzung: nordlicht_geomag.py, nordlicht_darkness.py und
nordlicht_cloud_era5.py (aggregate) vorher gelaufen.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Import der Geomag-Funktion direkt statt einer Zwischendatei -
# reine Formel, kein Grund fuer einen dritten JSON-Umweg
from nordlicht_geomag import geomag_latitude

ORTE = [
    ("tromsoe", "Tromsø", "Norwegen", 69.6517, 18.9556),
    ("abisko", "Abisko", "Schweden", 68.3541, 18.7871),
    ("rovaniemi", "Rovaniemi", "Finnland", 66.5039, 25.7294),
    ("reykjavik", "Reykjavik", "Island", 64.1466, -21.9426),
    ("yellowknife", "Yellowknife", "Kanada", 62.4540, -114.3718),
]
MONATE = ["sep", "okt", "nov", "dez", "jan", "feb", "mär"]

# Bekannte Grenzen der Wolken-Klimatologie: ERA5 unterschaetzt lokale
# orografische Effekte (Regenschatten) in komplexem Gelaende, weil die
# Modell-Topografie geglaettet ist - dokumentierte Schwaeche von Reanalyse-
# Produkten. Abisko ist ein bekannter Fall: p_clear liegt hier bei uns
# durchgehend UNTER Tromsø, waehrend meteorologische Messungen vor Ort
# (Aurora Sky Station, seit 1989) das Gegenteil zeigen - ca. 30-40% mehr
# klare Naechte als Tromsø, durch den "Blue Hole"-Effekt der umliegenden
# Berge. Ein zweiter, unabhaengiger Faktor: die Station liegt auf 900m und
# damit oft oberhalb tiefer Stratus-Schichten, die unser saeulenintegrierter
# tcc-Wert nicht von durchgehender Bewoelkung unterscheidet.
BEKANNTE_EINSCHRAENKUNGEN = {
    "abisko": (
        "Unsere Wolkenklimatologie basiert auf ERA5 und unterschaetzt hier "
        "vermutlich den realen Vorteil: Abiskos dokumentierter Regenschatten-"
        "Effekt (der \"Blue Hole\") ist kleinraeumiger, als das Modellraster "
        "gut abbilden kann, und die Aurora Sky Station liegt auf 900m Hoehe "
        "oberhalb tiefer Wolkenschichten, die unser Wert nicht separat erfasst."
    ),
}


def main():
    cloud = json.loads((BASE / "data" / "cloud_stats_nordlicht.json").read_text())
    darkness = json.loads((BASE / "data" / "nordlicht_darkness.json").read_text())

    ergebnis = []
    for slug, name, land, lat, lon in ORTE:
        geomag = round(geomag_latitude(lat, lon), 1)
        monatswerte = {}
        for m in MONATE:
            p_clear = cloud[slug][m]["p_clear"]
            dunkelstunden = darkness[slug][m]["dunkelstunden"]
            index = round(dunkelstunden * p_clear, 2)
            monatswerte[m] = {
                "dunkelstunden": dunkelstunden,
                "p_clear": p_clear,
                "mean_tcc": cloud[slug][m]["mean_tcc"],
                "index": index,
            }

        bester_monat = max(monatswerte, key=lambda m: monatswerte[m]["index"])

        eintrag = {
            "slug": slug,
            "name": name,
            "land": land,
            "lat": lat,
            "lon": lon,
            "geomag_lat": geomag,
            "bester_monat": bester_monat,
            "monate": monatswerte,
        }
        if slug in BEKANNTE_EINSCHRAENKUNGEN:
            eintrag["einschraenkung"] = BEKANNTE_EINSCHRAENKUNGEN[slug]

        ergebnis.append(eintrag)

    # Sortiert nach geomagnetischer Breite, wie in der urspruenglichen Analyse
    ergebnis.sort(key=lambda o: -o["geomag_lat"])

    out = BASE / "data" / "nordlicht_orte.json"
    out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print(f"✓ {out}\n")

    print(f"{'Ort':<14}{'geomag':>8}  {'bester Monat':<14}{'Index (bester Monat)':>22}")
    for o in ergebnis:
        bm = o["bester_monat"]
        print(f"{o['name']:<14}{o['geomag_lat']:>7.1f}°  {bm:<14}{o['monate'][bm]['index']:>20.2f}")


if __name__ == "__main__":
    main()
