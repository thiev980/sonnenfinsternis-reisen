#!/usr/bin/env python3
"""
Berechnet die lokalen Umstände der totalen Sonnenfinsternis vom 2. August 2027
für eine feste Ortsliste: Kontaktzeiten, Totalitätsdauer, Sonnenhöhe, Bedeckungsgrad.

Methode: topozentrische scheinbare Positionen von Sonne und Mond (skyfield, DE421),
Kontakte über Vorzeichenwechsel von f(t) = Separation - (R_mond ± R_sonne),
verfeinert per Bisektion auf ~0.05 s.

Genauigkeit: typischerweise wenige Sekunden gegenüber Espenak/NASA -- völlig
ausreichend für Reiseplanungs-Content. (Kein Limb-Profil / kein Delta-T-Risiko
auf diese kurze Distanz.)

Output: data/eclipse_raw.json
"""

import json
import numpy as np
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timezone

from skyfield.api import load, load_file, wgs84
from skyfield_data import get_skyfield_data_path

# --- Konstanten -------------------------------------------------------------
R_SUN_KM = 696_000.0          # IAU-Sonnenradius
K_MOON = 0.272281             # Espenaks k fuer totale Phasen (Mondradius/Erdradius)
R_MOON_KM = K_MOON * 6378.137 # ~1736.7 km

DATE = (2027, 8, 2)
WINDOW_UTC = (6.5, 13.5)      # Stunden UTC, deckt alle Phasen von Atlantik bis Arabien
COARSE_STEP_S = 5.0

BASE = Path(__file__).resolve().parent.parent

# --- Ortsliste --------------------------------------------------------------
# (slug, Name, Land, lat, lon, Hoehe m, IANA-Zeitzone, Kategorie)
PLACES = [
    # Spanien - Provinz Cadiz / Atlantik
    ("tarifa",        "Tarifa",                "Spanien",   36.014, -5.606,   5, "Europe/Madrid", "kern"),
    ("cadiz",         "Cádiz",                 "Spanien",   36.529, -6.293,  10, "Europe/Madrid", "kern"),
    ("jerez",         "Jerez de la Frontera",  "Spanien",   36.685, -6.126,  55, "Europe/Madrid", "kern"),
    ("conil",         "Conil de la Frontera",  "Spanien",   36.277, -6.089,  40, "Europe/Madrid", "kern"),
    ("vejer",         "Vejer de la Frontera",  "Spanien",   36.252, -5.965, 190, "Europe/Madrid", "kern"),
    ("zahara",        "Zahara de los Atunes",  "Spanien",   36.135, -5.846,   5, "Europe/Madrid", "kern"),
    ("algeciras",     "Algeciras",             "Spanien",   36.140, -5.456,  20, "Europe/Madrid", "kern"),
    ("gibraltar",     "Gibraltar",             "Gibraltar", 36.140, -5.353,  10, "Europe/Gibraltar", "kern"),
    # Spanien - Costa del Sol / Inland
    ("estepona",      "Estepona",              "Spanien",   36.428, -5.146,  20, "Europe/Madrid", "kern"),
    ("marbella",      "Marbella",              "Spanien",   36.510, -4.886,  30, "Europe/Madrid", "kern"),
    ("fuengirola",    "Fuengirola",            "Spanien",   36.541, -4.625,  10, "Europe/Madrid", "kern"),
    ("malaga",        "Málaga",                "Spanien",   36.721, -4.421,  10, "Europe/Madrid", "rand"),
    ("ronda",         "Ronda",                 "Spanien",   36.746, -5.161, 740, "Europe/Madrid", "rand"),
    ("sevilla",       "Sevilla",               "Spanien",   37.389, -5.984,  10, "Europe/Madrid", "partiell"),
    ("granada",       "Granada",               "Spanien",   37.177, -3.598, 680, "Europe/Madrid", "partiell"),
    ("almeria",       "Almería",               "Spanien",   36.834, -2.464,  20, "Europe/Madrid", "rand"),
    ("ceuta",         "Ceuta",                 "Spanien",   35.889, -5.316,  10, "Africa/Ceuta", "kern"),
    ("melilla",       "Melilla",               "Spanien",   35.292, -2.938,  20, "Africa/Ceuta", "kern"),
    ("palma",         "Palma de Mallorca",     "Spanien",   39.570,  2.650,  10, "Europe/Madrid", "partiell"),
    # Marokko
    ("tanger",        "Tanger",                "Marokko",   35.759, -5.834,  20, "Africa/Casablanca", "kern"),
    ("asilah",        "Asilah",                "Marokko",   35.465, -6.035,  10, "Africa/Casablanca", "kern"),
    ("tetouan",       "Tétouan",               "Marokko",   35.577, -5.368,  90, "Africa/Casablanca", "kern"),
    ("chefchaouen",   "Chefchaouen",           "Marokko",   35.169, -5.264, 560, "Africa/Casablanca", "kern"),
    ("al-hoceima",    "Al Hoceïma",            "Marokko",   35.244, -3.931,  40, "Africa/Casablanca", "kern"),
    ("nador",         "Nador",                 "Marokko",   35.168, -2.933,  10, "Africa/Casablanca", "kern"),
    ("fes",           "Fès",                   "Marokko",   34.033, -5.000, 410, "Africa/Casablanca", "partiell"),
    # Algerien / Tunesien
    ("oran",          "Oran",                  "Algerien",  35.699, -0.635,  90, "Africa/Algiers", "kern"),
    ("algier",        "Algier",                "Algerien",  36.754,  3.059,  20, "Africa/Algiers", "rand"),
    ("tunis",         "Tunis",                 "Tunesien",  36.806, 10.181,  10, "Africa/Tunis", "rand"),
    ("kairouan",      "Kairouan",              "Tunesien",  35.678, 10.096,  60, "Africa/Tunis", "kern"),
    ("sousse",        "Sousse",                "Tunesien",  35.826, 10.637,  10, "Africa/Tunis", "kern"),
    ("monastir",      "Monastir",              "Tunesien",  35.778, 10.826,  10, "Africa/Tunis", "kern"),
    ("sfax",          "Sfax",                  "Tunesien",  34.740, 10.760,  10, "Africa/Tunis", "kern"),
    ("djerba",        "Djerba (Houmt Souk)",   "Tunesien",  33.876, 10.857,   5, "Africa/Tunis", "kern"),
    ("lampedusa",     "Lampedusa",             "Italien",   35.502, 12.606,  20, "Europe/Rome", "kern"),
    # Libyen
    ("benghazi",      "Bengasi",               "Libyen",    32.117, 20.067,  10, "Africa/Tripoli", "kern"),
    # Aegypten
    ("siwa",          "Siwa-Oase",             "Ägypten",   29.204, 25.519, -15, "Africa/Cairo", "kern"),
    ("kairo",         "Kairo",                 "Ägypten",   30.044, 31.236,  20, "Africa/Cairo", "partiell"),
    ("sohag",         "Sohag",                 "Ägypten",   26.556, 31.695,  60, "Africa/Cairo", "kern"),
    ("girga",         "Girga",                 "Ägypten",   26.336, 31.891,  65, "Africa/Cairo", "kern"),
    ("qena",          "Qena",                  "Ägypten",   26.161, 32.727,  75, "Africa/Cairo", "kern"),
    ("luxor",         "Luxor",                 "Ägypten",   25.687, 32.640,  75, "Africa/Cairo", "kern"),
    ("hurghada",      "Hurghada",              "Ägypten",   27.258, 33.812,   5, "Africa/Cairo", "rand"),
    ("el-gouna",      "El Gouna",              "Ägypten",   27.394, 33.678,   5, "Africa/Cairo", "rand"),
    ("safaga",        "Safaga",                "Ägypten",   26.729, 33.936,   5, "Africa/Cairo", "kern"),
    ("marsa-alam",    "Marsa Alam",            "Ägypten",   25.063, 34.890,  10, "Africa/Cairo", "kern"),
    ("assuan",        "Assuan",                "Ägypten",   24.089, 32.899, 100, "Africa/Cairo", "partiell"),
    # Saudi-Arabien
    ("dschidda",      "Dschidda",              "Saudi-Arabien", 21.543, 39.173, 10, "Asia/Riyadh", "kern"),
    ("mekka",         "Mekka",                 "Saudi-Arabien", 21.389, 39.857, 280, "Asia/Riyadh", "kern"),
    # DACH & Referenz (nur partiell) - fuer die "Sichtbarkeit zuhause"-Seiten
    ("zuerich",       "Zürich",                "Schweiz",   47.377,  8.541, 410, "Europe/Zurich", "partiell"),
    ("bern",          "Bern",                  "Schweiz",   46.948,  7.447, 540, "Europe/Zurich", "partiell"),
    ("muenchen",      "München",               "Deutschland", 48.137, 11.575, 520, "Europe/Berlin", "partiell"),
    ("frankfurt",     "Frankfurt am Main",     "Deutschland", 50.110,  8.682, 110, "Europe/Berlin", "partiell"),
    ("berlin",        "Berlin",                "Deutschland", 52.520, 13.405,  35, "Europe/Berlin", "partiell"),
    ("wien",          "Wien",                  "Österreich", 48.208, 16.373, 170, "Europe/Vienna", "partiell"),
    ("rom",           "Rom",                   "Italien",   41.893, 12.483,  20, "Europe/Rome", "partiell"),
]

# --- Setup ------------------------------------------------------------------
data_path = Path(get_skyfield_data_path())
ts = load.timescale(builtin=True)
eph = load_file(str(data_path / "de421.bsp"))
earth, sun, moon = eph["earth"], eph["sun"], eph["moon"]


def circumstances(lat, lon, elev_m):
    """Berechnet alle Kontakt-Zeiten & Kennzahlen fuer einen Ort."""
    site = earth + wgs84.latlon(lat, lon, elevation_m=elev_m)

    # Grobes Zeitraster (vektorisiert)
    h0, h1 = WINDOW_UTC
    n = int((h1 - h0) * 3600 / COARSE_STEP_S) + 1
    hours = np.linspace(h0, h1, n)
    t = ts.utc(*DATE, hours)

    astro = site.at(t)
    s = astro.observe(sun).apparent()
    m = astro.observe(moon).apparent()

    sep = s.separation_from(m).radians
    r_sun = np.arcsin(R_SUN_KM / s.distance().km)
    r_moon = np.arcsin(R_MOON_KM / m.distance().km)

    f_partial = sep - (r_moon + r_sun)   # < 0: partielle Phase laeuft
    f_total = sep - (r_moon - r_sun)     # < 0: Totalitaet laeuft

    def refine(f_at, lo, hi, target_sign_change=True, tol=0.05 / 86400.0):
        """Bisektion auf Vorzeichenwechsel von f zwischen zwei Zeitpunkten (jd)."""
        flo = f_at(lo)
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            fm = f_at(mid)
            if (flo < 0) == (fm < 0):
                lo, flo = mid, fm
            else:
                hi = mid
            if hi - lo < tol:
                break
        return 0.5 * (lo + hi)

    def f_scalar(kind):
        def _f(jd):
            tt = ts.tt_jd(jd)
            a = site.at(tt)
            ss = a.observe(sun).apparent()
            mm = a.observe(moon).apparent()
            sp = ss.separation_from(mm).radians
            rs = np.arcsin(R_SUN_KM / ss.distance().km)
            rm = np.arcsin(R_MOON_KM / mm.distance().km)
            return sp - ((rm + rs) if kind == "partial" else (rm - rs))
        return _f

    def find_contacts(f_arr, kind):
        idx = np.where(np.diff(np.sign(f_arr)) != 0)[0]
        out = []
        fs = f_scalar(kind)
        for i in idx:
            jd = refine(fs, t.tt[i], t.tt[i + 1])
            out.append(jd)
        return out

    partial_contacts = find_contacts(f_partial, "partial")
    total_contacts = find_contacts(f_total, "total")

    # Maximum: minimale Separation (parabolische Verfeinerung auf dem Raster)
    i_min = int(np.argmin(sep))
    i0, i1 = max(i_min - 1, 0), min(i_min + 1, len(sep) - 1)
    y0, y1, y2 = sep[i0], sep[i_min], sep[i1]
    denom = (y0 - 2 * y1 + y2)
    shift = 0.5 * (y0 - y2) / denom if denom != 0 else 0.0
    jd_max = t.tt[i_min] + shift * (COARSE_STEP_S / 86400.0)
    t_max = ts.tt_jd(jd_max)

    # Kennzahlen am Maximum
    a = site.at(t_max)
    ss = a.observe(sun).apparent()
    mm = a.observe(moon).apparent()
    alt, az, _ = ss.altaz()
    sp = float(ss.separation_from(mm).radians)
    rs = float(np.arcsin(R_SUN_KM / ss.distance().km))
    rm = float(np.arcsin(R_MOON_KM / mm.distance().km))

    obscuration = disk_obscuration(sp, rs, rm)
    magnitude = (rs + rm - sp) / (2 * rs)  # Standarddefinition

    result = {
        "partial_contacts_tt_jd": partial_contacts,
        "total_contacts_tt_jd": total_contacts,
        "t_max_tt_jd": float(jd_max),
        "sun_alt_max_deg": round(float(alt.degrees), 1),
        "sun_az_max_deg": round(float(az.degrees), 1),
        "obscuration_max": round(float(obscuration), 4),
        "magnitude_max": round(float(magnitude), 4),
    }
    return result


def disk_obscuration(sep, r_sun, r_moon):
    """Anteil der Sonnenscheibe, der vom Mond bedeckt ist (Kreis-Ueberlappung)."""
    if sep >= r_sun + r_moon:
        return 0.0
    if sep <= r_moon - r_sun:
        return 1.0
    if sep <= r_sun - r_moon:
        return (r_moon / r_sun) ** 2
    d1 = (sep**2 + r_sun**2 - r_moon**2) / (2 * sep)
    d2 = sep - d1
    area = (
        r_sun**2 * np.arccos(np.clip(d1 / r_sun, -1, 1))
        - d1 * np.sqrt(max(r_sun**2 - d1**2, 0.0))
        + r_moon**2 * np.arccos(np.clip(d2 / r_moon, -1, 1))
        - d2 * np.sqrt(max(r_moon**2 - d2**2, 0.0))
    )
    return float(area / (np.pi * r_sun**2))


def jd_to_iso(jd_tt, tzname):
    t = ts.tt_jd(jd_tt)
    dt_utc = t.utc_datetime()
    dt_loc = dt_utc.astimezone(ZoneInfo(tzname))
    return dt_utc.strftime("%H:%M:%S"), dt_loc.strftime("%H:%M:%S")


def fmt_duration(seconds):
    mns, s = divmod(int(round(seconds)), 60)
    return f"{mns}m {s:02d}s"


def main():
    out = []
    for slug, name, country, lat, lon, elev, tzname, cat in PLACES:
        c = circumstances(lat, lon, elev)
        pc, tc = c["partial_contacts_tt_jd"], c["total_contacts_tt_jd"]

        rec = {
            "slug": slug, "name": name, "country": country,
            "lat": lat, "lon": lon, "elev_m": elev, "tz": tzname,
            "category": cat,
            "is_total": len(tc) >= 2,
            "sun_alt_max_deg": c["sun_alt_max_deg"],
            "sun_az_max_deg": c["sun_az_max_deg"],
            "obscuration_pct": round(c["obscuration_max"] * 100, 1),
            "magnitude": c["magnitude_max"],
        }

        if len(pc) >= 2:
            u, l = jd_to_iso(pc[0], tzname); rec["c1_utc"], rec["c1_local"] = u, l
            u, l = jd_to_iso(pc[-1], tzname); rec["c4_utc"], rec["c4_local"] = u, l
        u, l = jd_to_iso(c["t_max_tt_jd"], tzname)
        rec["max_utc"], rec["max_local"] = u, l

        if rec["is_total"]:
            dur = (tc[1] - tc[0]) * 86400.0
            u, l = jd_to_iso(tc[0], tzname); rec["c2_utc"], rec["c2_local"] = u, l
            u, l = jd_to_iso(tc[1], tzname); rec["c3_utc"], rec["c3_local"] = u, l
            rec["totality_s"] = round(dur, 1)
            rec["totality_str"] = fmt_duration(dur)

        out.append(rec)
        tot = rec.get("totality_str", "-")
        print(f"{name:24s} {country:14s} total={str(rec['is_total']):5s} "
              f"Dauer={tot:9s} Bedeckung={rec['obscuration_pct']:5.1f}% "
              f"max lokal={rec['max_local']} Sonnenhöhe={rec['sun_alt_max_deg']:5.1f}°")

    dest = BASE / "data" / "eclipse_raw.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n→ {dest} ({len(out)} Orte)")


if __name__ == "__main__":
    main()
