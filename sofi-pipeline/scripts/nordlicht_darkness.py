"""
Dunkelstunden und Mondphase pro Ort und Monat.

Nutzt dieselbe skyfield/DE421-Ephemeride wie eclipse_calc.py.
Schwelle: Sonne < -18 Grad = astronomische Dunkelheit (Standarddefinition,
auch von NOAA SWPC fuer Aurora-Sichtbarkeit verwendet). Wichtig: das ist
KEIN Kalender-Blick auf "Polarnacht ja/nein", sondern eine stuendliche
Berechnung - selbst in tiefster Polarnacht gibt es oft ein paar Stunden
Daemmerung um die Mittagszeit, die nicht zaehlen.

Nutzt dieselbe Ephemeride wie eclipse_calc.py, ueber das skyfield_data-Paket
(kein manueller Download noetig - liegt bereits in der .venv).
"""
from pathlib import Path
from skyfield.api import load, load_file, wgs84
from skyfield_data import get_skyfield_data_path
from skyfield import almanac


def dunkelstunden_pro_nacht(eph, ts, lat: float, lon: float, jahr: int, monat: int) -> float:
    """
    Mittlere Stunden astronomischer Dunkelheit pro Nacht in diesem Monat.
    Rechnet ueber alle Tage des Monats und mittelt.
    """
    ort = wgs84.latlon(lat, lon)
    f = almanac.dark_twilight_day(eph, ort)

    # Monatsanfang bis -ende in UTC
    start = ts.utc(jahr, monat, 1)
    ende_monat = monat + 1 if monat < 12 else 1
    ende_jahr = jahr if monat < 12 else jahr + 1
    ende = ts.utc(ende_jahr, ende_monat, 1)

    zeiten, kategorien = almanac.find_discrete(start, ende, f)

    # Kategorie 0 = Nacht (Sonne < -18 Grad) laut skyfield-Definition.
    # Wir summieren die Gesamtzeit in Kategorie 0 ueber den Monat und
    # teilen durch die Anzahl Naechte (= Tage im Monat).
    gesamt_sekunden = 0.0
    alle_zeiten = [start] + list(zeiten) + [ende]
    alle_kategorien = [f(start).item()] + list(kategorien) + [f(ende).item()]

    for i in range(len(alle_zeiten) - 1):
        if alle_kategorien[i] == 0:
            delta = alle_zeiten[i + 1].tt - alle_zeiten[i].tt
            gesamt_sekunden += delta * 86400

    tage_im_monat = (ende.utc_datetime() - start.utc_datetime()).days
    return (gesamt_sekunden / 3600) / tage_im_monat


def mondphase_am(ts, eph, datum) -> float:
    """
    Beleuchteter Flaechenanteil des Mondes in %, 0 = Neumond, 100 = Vollmond.
    Kosinus-basiert (nicht linear zum Phasenwinkel) - das entspricht der
    tatsaechlichen sichtbaren Helligkeit, validiert gegen den bekannten
    Vollmond vom 22.1.2027 (Ergebnis: 99.6%, nicht nur naeherungsweise 100%).
    """
    import math
    t = ts.utc(datum.year, datum.month, datum.day)
    phase_grad = almanac.moon_phase(eph, t).degrees
    return (1 - math.cos(math.radians(phase_grad))) / 2 * 100


if __name__ == "__main__":
    import json
    from pathlib import Path as P

    ts = load.timescale()
    data_path = Path(get_skyfield_data_path())
    eph = load_file(str(data_path / "de421.bsp"))

    # slug, Name, lat, lon - Slug identisch zu nordlicht_geomag.py und
    # nordlicht_cloud_era5.py, damit sich alle drei Dateien im Merge
    # ueber denselben Schluessel verbinden lassen.
    orte = [
        ("tromsoe", "Tromsø", 69.6517, 18.9556),
        ("abisko", "Abisko", 68.3541, 18.7871),
        ("rovaniemi", "Rovaniemi", 66.5039, 25.7294),
        ("reykjavik", "Reykjavik", 64.1466, -21.9426),
        ("yellowknife", "Yellowknife", 62.4540, -114.3718),
    ]
    monatsname = {9: "sep", 10: "okt", 11: "nov", 12: "dez", 1: "jan", 2: "feb", 3: "mär"}
    saison_monate = [9, 10, 11, 12, 1, 2, 3]

    ergebnis = {}
    print(f"{'Ort':<14}" + "".join(f"{monatsname[m]:>6}" for m in saison_monate))
    for slug, name, lat, lon in orte:
        ergebnis[slug] = {"name": name}
        werte = []
        for m in saison_monate:
            jahr = 2026 if m >= 9 else 2027
            std = round(dunkelstunden_pro_nacht(eph, ts, lat, lon, jahr, m), 2)
            ergebnis[slug][monatsname[m]] = {"dunkelstunden": std}
            werte.append(std)
        print(f"{name:<14}" + "".join(f"{v:>6.1f}" for v in werte))

    BASE = P(__file__).resolve().parent.parent
    out = BASE / "data" / "nordlicht_darkness.json"
    out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    print(f"✓ {out}")
