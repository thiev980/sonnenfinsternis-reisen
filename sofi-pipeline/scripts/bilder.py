"""Headerbilder von Wikimedia Commons für astroreisen.com.

  python sofi-pipeline/scripts/bilder.py kandidaten   # Foto-Kandidaten je offener Seite → bilder/kandidaten.json
  python sofi-pipeline/scripts/bilder.py vorschau     # 500-px-Vorschauen der offenen Kandidaten → vorschau/
  python sofi-pipeline/scripts/bilder.py laden        # gewählte Bilder (bilder/auswahl.yaml) herunterladen
                                                      # → sofi-site/src/assets/bilder, Nachweise → src/data/bilder.json

Braucht Netz (Commons/Wikidata) und läuft deshalb im Workflow «Bilder aktualisieren»;
aus der Claude-Cloud-Session ist Wikimedia nicht erreichbar. Vorlage: etappen-pipeline/etappen/bilder.py.

Seiten (Schlüssel):
  sofi/<slug>        Sonnenfinsternis-Ortsseite  – nur Orte mit Redaktionstext (src/texte/sonnenfinsternis/<slug>.md)
  nordlicht/<slug>   Nordlicht-Ortsseite
  guide/<slug>       Guide (Content Collection, ohne draft)
  seite/<name>       Übersichtsseite (start, sonnenfinsternis, nordlichter) – Liste in bilder/seiten.yaml

Kandidaten für Orte: Wikidata-Bild (P18) des Orts (Treffer nur, wenn die Wikidata-Koordinate nahe an
unserer liegt) plus Commons-Geosuche um die Koordinaten; bei Nordlicht-Orten zusätzlich eine Commons-
Textsuche «<Ort> aurora». Für Guides und Übersichtsseiten: Commons-Textsuche und Geosuche um die in
bilder/seiten.yaml genannten Orte.

Lizenz: nur CC0, Public Domain, CC BY und CC BY-SA. Jede Seite zeigt Urheber, Lizenz und Link.
Die Bilder werden selbst gehostet (kein Abruf bei Wikimedia im Browser der Besucher).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import math
import re
import sys
import time
from pathlib import Path

import requests
import yaml

log = logging.getLogger("bilder")

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "sofi-site" / "src"
DATA = SITE / "data"
ASSETS = SITE / "assets" / "bilder"
BILDER = ROOT / "sofi-pipeline" / "bilder"
KANDIDATEN = BILDER / "kandidaten.json"
AUSWAHL = BILDER / "auswahl.yaml"
SEITEN = BILDER / "seiten.yaml"
BILDER_JSON = DATA / "bilder.json"
VORSCHAU = ROOT / "vorschau"

COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKIDATA = "https://www.wikidata.org/w/api.php"
UA = "astroreisen.com/0.1 (https://astroreisen.com; thierry.figini@gmail.com) python-requests"
BREITE_HEADER, BREITE_VORSCHAU = 1920, 500
PRO_SEITE = 8

LIZENZ_OK = re.compile(r"^(cc0|public domain|pd|cc[ -]by(-sa)?( \d(\.\d)?)?\b|attribution)", re.I)
TITEL_RAUS = re.compile(
    r"karte|\bmap\b|\bplan\b|wappen|coat.of.arms|schild|\bsign\b|tafel|innen|interior|inside|orgel|altar|"
    r"fenster|window|grab|epitaph|logo|diagram|fahne|flag|portrait|porträt|briefmarke|stamp|"
    r"postkarte|postcard|\bdetail\b|inschrift|inscription|relief|skulptur|sculpture|statue|gemälde|painting|"
    r"museum|exhibit|poster|screenshot|chart|graph|satellite|locator",
    re.I,
)

_s = requests.Session()
_s.headers["User-Agent"] = UA


def _get(url: str, params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": 2}
    for versuch in range(5):
        r = _s.get(url, params=params, timeout=60)
        if r.status_code in (429, 503):
            time.sleep(5 * (versuch + 1))
            continue
        r.raise_for_status()
        time.sleep(0.2)
        return r.json()
    r.raise_for_status()
    return {}


def _text(v: str | None) -> str:
    t = html.unescape(re.sub(r"<[^>]+>", " ", v or ""))
    return re.sub(r"\s+", " ", t).strip()


def _abstand_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


# --------------------------------------------------------------------------- Commons / Wikidata

def wikidata_bild(name: str, lat: float, lon: float, qid: str | None = None, max_km: float = 25) -> str | None:
    """P18 des Wikidata-Objekts zum Ort. Ohne feste Q-ID: Suche per Name, nur Treffer mit P625 nahe (lat, lon)."""
    if qid:
        ids = [qid]
    else:
        namen = [name, re.sub(r"\s*\(.*?\)", "", name)] + re.findall(r"\((.*?)\)", name)
        ids = []
        for n in dict.fromkeys(x.strip() for x in namen if x.strip()):
            for sprache in ("de", "en"):
                d = _get(WIKIDATA, {"action": "wbsearchentities", "search": n, "language": sprache,
                                    "type": "item", "limit": 7})
                ids += [x["id"] for x in d.get("search", []) if x["id"] not in ids]
    if not ids:
        return None
    d = _get(WIKIDATA, {"action": "wbgetentities", "ids": "|".join(ids[:50]), "props": "claims"})
    ents = d.get("entities") or {}
    for q in ids:
        claims = (ents.get(q) or {}).get("claims") or {}
        if not qid:
            koord = [c.get("mainsnak", {}).get("datavalue", {}).get("value") for c in claims.get("P625", [])]
            koord = [k for k in koord if k]
            if not koord or min(_abstand_km((lat, lon), (k["latitude"], k["longitude"])) for k in koord) > max_km:
                continue
        for c in claims.get("P18", []):
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            if v:
                log.info("  Wikidata %s → %s", q, v)
                return "File:" + v
    return None


def geosuche(lat: float, lon: float, radius: int) -> list[str]:
    d = _get(COMMONS, {"action": "query", "list": "geosearch", "gsnamespace": 6,
                       "gscoord": f"{lat}|{lon}", "gsradius": min(radius, 10000), "gslimit": 100})
    return [x["title"] for x in d.get("query", {}).get("geosearch", [])]


def textsuche(begriff: str, anzahl: int = 50) -> list[str]:
    d = _get(COMMONS, {"action": "query", "list": "search", "srnamespace": 6,
                       "srsearch": f"{begriff} filetype:bitmap", "srlimit": anzahl})
    return [x["title"] for x in d.get("query", {}).get("search", [])]


def bildinfo(titel: list[str], breite: int = BREITE_HEADER) -> dict[str, dict]:
    """Metadaten und Vorschau-URL je Commons-Datei; nur passende Lizenzen."""
    out: dict[str, dict] = {}
    titel = sorted(set(titel))
    for i in range(0, len(titel), 50):
        d = _get(COMMONS, {"action": "query", "titles": "|".join(titel[i:i + 50]), "prop": "imageinfo",
                           "iiprop": "url|size|mime|extmetadata", "iiurlwidth": breite,
                           "iiextmetadatafilter": "Artist|Credit|LicenseShortName|LicenseUrl|Categories"})
        for p in d.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [None])[0]
            if not ii:
                continue
            m = ii.get("extmetadata") or {}
            lizenz = _text(m.get("LicenseShortName", {}).get("value"))
            if not LIZENZ_OK.match(lizenz):
                continue
            autor = _text(m.get("Artist", {}).get("value")) or _text(m.get("Credit", {}).get("value")) or "unbekannt"
            out[p["title"]] = {
                "datei": p["title"],
                "url": ii.get("thumburl") or ii["url"],
                "breite": ii.get("width"), "hoehe": ii.get("height"), "mime": ii.get("mime"),
                "autor": autor[:120], "lizenz": lizenz,
                "lizenz_url": _text(m.get("LicenseUrl", {}).get("value")) or None,
                "seite": ii.get("descriptionurl"),
                "kategorien": _text(m.get("Categories", {}).get("value")),
            }
    return out


def _vorschau_url(url: str, breite: int = BREITE_VORSCHAU) -> str:
    return re.sub(r"/\d+px-", f"/{breite}px-", url) if "/thumb/" in url else url


def _wertung(info: dict, quelle: str) -> float:
    w = 0.0
    kat = info["kategorien"]
    if "Featured pictures" in kat:
        w += 4
    if "Quality images" in kat:
        w += 3
    if "Valued images" in kat:
        w += 2
    if quelle.startswith("Wikidata"):
        w += 3
    if (info["breite"] or 0) >= 3000:
        w += 1
    return w


def _passt(info: dict) -> bool:
    b, h = info["breite"] or 0, info["hoehe"] or 1
    return (info["mime"] == "image/jpeg" and b >= 1600 and 1.25 <= b / h <= 2.6
            and not TITEL_RAUS.search(info["datei"]))


# --------------------------------------------------------------------------- Seiten

def _frontmatter(p: Path) -> dict:
    t = p.read_text()
    m = re.match(r"^---\n(.*?)\n---", t, re.S)
    return yaml.safe_load(m.group(1)) or {} if m else {}


def _konfig() -> dict:
    return yaml.safe_load(SEITEN.read_text()) or {} if SEITEN.exists() else {}


def seiten() -> list[dict]:
    """Alle Seiten, die ein Headerbild bekommen können: {key, bereich, titel, ...Suchangaben}."""
    konf = _konfig()
    ueber = konf.get("orte") or {}
    sofi = json.loads((DATA / "orte.json").read_text())
    nl = json.loads((DATA / "nordlicht_orte.json").read_text())
    alle_orte = {o["slug"]: o for o in sofi} | {o["slug"]: o for o in nl}
    out = []
    for name, v in (konf.get("seiten") or {}).items():
        out.append({"key": f"seite/{name}", "bereich": "Übersichtsseiten", "titel": v["titel"],
                    "suche": v.get("suche", []), "orte": v.get("orte", [])})
    for p in sorted((SITE / "content" / "guides").glob("*.md")):
        fm = _frontmatter(p)
        if fm.get("draft"):
            continue
        v = (konf.get("guides") or {}).get(p.stem) or {}
        section = fm.get("section", "sonnenfinsternis")
        standard = konf.get("guide_standard", {}).get(section, {})
        out.append({"key": f"guide/{p.stem}", "bereich": "Guides", "titel": fm.get("heading") or fm.get("title"),
                    "suche": v.get("suche", standard.get("suche", [])), "orte": v.get("orte", standard.get("orte", []))})
    texte = {p.stem for p in (SITE / "texte" / "sonnenfinsternis").glob("*.md")}
    for o in sofi:
        if o["slug"] in texte:
            out.append({"key": f"sofi/{o['slug']}", "bereich": "Sonnenfinsternis-Orte",
                        "titel": f"{o['name']} ({o['country']})", "ort": o, "ueber": ueber.get(o["slug"], {})})
    for o in nl:
        out.append({"key": f"nordlicht/{o['slug']}", "bereich": "Nordlicht-Orte",
                    "titel": f"{o['name']} ({o['land']})", "ort": o, "ueber": ueber.get(o["slug"], {}),
                    "suche": [f'"{o["name"]}" aurora']})
    for s in out:
        s["orte"] = [alle_orte[x] for x in s.get("orte", []) if x in alle_orte]
    return out


def kandidaten() -> dict:
    ergebnis: dict = json.loads(KANDIDATEN.read_text()) if KANDIDATEN.exists() else {}
    entschieden = entschiedene_schluessel()
    for s in seiten():
        if s["key"] in entschieden or s["key"] in ergebnis:
            continue          # schon entschieden oder schon Kandidaten gesucht
        log.info("%s", s["key"])
        quellen: dict[str, str] = {}
        if "ort" in s:
            o, u = s["ort"], s["ueber"]
            t = wikidata_bild(o["name"], o["lat"], o["lon"], u.get("wikidata"))
            if t:
                quellen[t] = f"Wikidata-Bild von {o['name']}"
            for t in geosuche(o["lat"], o["lon"], u.get("radius", 3000)):
                quellen.setdefault(t, f"bis {u.get('radius', 3000) // 1000} km um {o['name']}")
        for o in s.get("orte", []):
            for t in geosuche(o["lat"], o["lon"], 3000):
                quellen.setdefault(t, f"bei {o['name']}")
        for b in s.get("suche", []):
            for t in textsuche(b):
                quellen.setdefault(t, f"Suche «{b}»")
        infos = bildinfo(list(quellen))
        liste = []
        for t, info in infos.items():
            if not _passt(info):
                continue
            liste.append({k: v for k, v in info.items() if k not in ("kategorien", "mime")}
                         | {"vorschau": _vorschau_url(info["url"]), "quelle": quellen[t],
                            "wertung": _wertung(info, quellen[t])})
        liste.sort(key=lambda c: (-c["wertung"], c["datei"]))
        # Höchstens die Hälfte aus einer einzelnen Quelle, damit Wikidata, Geo- und Textsuche gemischt erscheinen
        pro_quelle: dict[str, int] = {}
        auswahl, rest = [], []
        for c in liste:
            if pro_quelle.get(c["quelle"], 0) < PRO_SEITE // 2:
                pro_quelle[c["quelle"]] = pro_quelle.get(c["quelle"], 0) + 1
                auswahl.append(c)
            else:
                rest.append(c)
        auswahl = (auswahl + rest)[:PRO_SEITE]
        ergebnis[s["key"]] = {"bereich": s["bereich"], "titel": s["titel"], "kandidaten": auswahl}
        log.info("%s: %d Kandidaten (von %d Dateien)", s["key"], len(auswahl), len(quellen))
    BILDER.mkdir(exist_ok=True)
    KANDIDATEN.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1) + "\n")
    return ergebnis


# --------------------------------------------------------------------------- Auswahl / Laden

BEREICHE = ["Übersichtsseiten", "Sonnenfinsternis-Orte", "Nordlicht-Orte", "Guides"]


def entschiedene_schluessel() -> set[str]:
    """Schlüssel in bilder/auswahl.yaml, auch die mit «kein»."""
    return set((yaml.safe_load(AUSWAHL.read_text()) or {}).keys()) if AUSWAHL.exists() else set()


def offene_gruppen() -> list[dict]:
    """Seiten ohne Entscheidung, mit ihren Kandidaten (für Vorschau und Auswahlseite)."""
    daten = json.loads(KANDIDATEN.read_text()) if KANDIDATEN.exists() else {}
    entschieden = entschiedene_schluessel()
    gruppen = [{"key": k, "bereich": v["bereich"], "titel": v["titel"], "kand": v["kandidaten"]}
               for k, v in daten.items() if k not in entschieden]
    gruppen.sort(key=lambda g: (BEREICHE.index(g["bereich"]) if g["bereich"] in BEREICHE else 9, g["titel"]))
    return gruppen


def vorschau_name(titel: str) -> str:
    return hashlib.sha1(titel.encode()).hexdigest()[:16] + ".jpg"


def _auswahl() -> dict[str, dict]:
    if not AUSWAHL.exists():
        return {}
    roh = yaml.safe_load(AUSWAHL.read_text()) or {}
    out = {}
    for k, v in roh.items():
        if isinstance(v, str):
            v = {"datei": v}
        if not v or not v.get("datei") or str(v["datei"]).lower() == "kein":
            continue
        d = str(v["datei"])
        out[k] = {"datei": d if d.startswith("File:") else "File:" + d, "fokus": v.get("fokus"), "alt": v.get("alt")}
    return out


def _herunterladen(url: str, ziel: Path) -> None:
    for versuch in range(5):
        r = _s.get(url, timeout=120)
        if r.status_code in (429, 503):
            time.sleep(10 * (versuch + 1))
            continue
        r.raise_for_status()
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(r.content)
        time.sleep(0.3)
        return
    r.raise_for_status()


def laden() -> None:
    alt = json.loads(BILDER_JSON.read_text()) if BILDER_JSON.exists() else {"seiten": {}}
    neu: dict = {"seiten": {}}
    behalten: set[Path] = set()
    for schluessel, wahl in _auswahl().items():
        pfad = f"{schluessel}.jpg"
        datei = ASSETS / pfad
        e = alt["seiten"].get(schluessel)
        if not (e and e.get("titel") == wahl["datei"] and datei.exists()):
            info = bildinfo([wahl["datei"]]).get(wahl["datei"])
            if not info:
                log.warning("%s: keine passende Lizenz oder nicht gefunden", wahl["datei"])
                continue
            _herunterladen(info["url"], datei)
            e = {"titel": wahl["datei"], "datei": pfad, "breite": info["breite"], "hoehe": info["hoehe"],
                 "autor": info["autor"], "lizenz": info["lizenz"], "lizenz_url": info["lizenz_url"],
                 "seite": info["seite"]}
        behalten.add(datei)
        e = {k: v for k, v in e.items() if k not in ("fokus", "alt")}
        neu["seiten"][schluessel] = e | {k: wahl[k] for k in ("fokus", "alt") if wahl.get(k)}
    if ASSETS.exists():
        for f in ASSETS.rglob("*.jpg"):
            if f not in behalten:
                f.unlink()
    BILDER_JSON.write_text(json.dumps(neu, ensure_ascii=False, indent=1) + "\n")
    log.info("Bilder: %d Headerbilder", len(neu["seiten"]))


def vorschau(ziel: Path = VORSCHAU) -> None:
    """Vorschaubilder (500 px) der Kandidaten aller offenen Seiten; Dateiname = SHA1 des Commons-Titels."""
    titel = {c["datei"]: c["vorschau"] for g in offene_gruppen() for c in g["kand"]}
    for t, url in sorted(titel.items()):
        f = ziel / vorschau_name(t)
        if not f.exists():
            try:
                _herunterladen(url, f)
            except requests.RequestException as e:
                log.warning("%s: %s", t, e)
    log.info("Vorschau: %d Dateien", len(list(ziel.glob("*.jpg"))) if ziel.exists() else 0)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("schritt", choices=["kandidaten", "vorschau", "laden", "seiten"])
    a = ap.parse_args(argv)
    if a.schritt == "kandidaten":
        kandidaten()
    elif a.schritt == "vorschau":
        vorschau()
    elif a.schritt == "laden":
        laden()
    else:   # offline: welche Seiten gäbe es, welche sind offen
        entschieden = entschiedene_schluessel()
        for s in seiten():
            print(("✓ " if s["key"] in entschieden else "  ") + s["key"], "·", s["titel"])


if __name__ == "__main__":
    main(sys.argv[1:])
