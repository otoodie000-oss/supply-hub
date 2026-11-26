"""Structured tables -> entity records.
  countries  mledoze/countries (ODbL 1.0) + countryinfo 1.1.0 (MIT; population ~2015)
  cities     geonamescache 3.0.2 (MIT; GeoNames CC BY 4.0; cities with population >= 15,000)
  us states  us 4.0.0 (BSD-3) + largest city computed from geonamescache
  elements   periodictable 2.1.0 (public domain) + period/group/category from the standard layout
  planets    hand-written table (flagged; values from standard references, moon counts as of 2023)
  airports   airportsdata 20261126 (MIT; IATA airports)
  books      zygmuntz/goodbooks-10k (CC BY-SA 4.0): first author, original publication year
Writes WORK/kb/src/tables.jsonl.gz"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import clean_text, writer, load_titles  # noqa: E402

RAW = "/home/user/work/x/raw"


def lc(s):
    return clean_text(s).lower().strip()


def num(n):
    return "{:,}".format(int(round(n)))


def continent(region, sub):
    if region == "Americas":
        return "south america" if sub == "South America" else "north america"
    if region == "Antarctic":
        return "antarctica"
    return {"Europe": "europe", "Asia": "asia", "Africa": "africa", "Oceania": "oceania"}.get(region)


def main():
    import countryinfo
    import geonamescache
    import us
    import periodictable
    import airportsdata
    titles = load_titles()
    out = writer("tables")
    stats = defaultdict(int)

    def emit(rec):
        rec.setdefault("aliases", [])
        rec["pop"] = rec.get("pop", titles.get(rec["name"], (0,))[0])
        for f in rec["facts"]:
            stats[rec["src"] + ":" + f[0]] += 1
        out.write(json.dumps(rec) + "\n")

    # ---------------- countries
    mled = json.load(open(os.path.join(RAW, "countries", "countries.json")))
    by3 = {c["cca3"]: c for c in mled}
    ci = {}
    for c in countryinfo.all_countries():
        try:
            d = c.info()
        except Exception:
            continue
        iso = (d.get("ISO") or {}).get("alpha3")
        if iso:
            ci[iso] = d
    cname = {c["cca3"]: lc(c["name"]["common"]) for c in mled}
    gc = geonamescache.GeonamesCache()
    cities = gc.get_cities()
    cc2name = {c["cca2"]: lc(c["name"]["common"]) for c in mled}
    capital_of = {}
    for c in mled:
        name = cname[c["cca3"]]
        facts = []
        cap = c.get("capital") or []
        if len(cap) == 1:
            facts.append(["capital", lc(cap[0])])
            capital_of[(lc(cap[0]), c["cca2"])] = name
        cont = continent(c.get("region"), c.get("subregion"))
        if cont:
            facts.append(["continent", cont])
        if c.get("subregion"):
            facts.append(["region", lc(c["subregion"])])
        if c.get("area") and c["area"] > 0:
            facts.append(["area", num(c["area"]) + " square kilometres"])
        cur = list((c.get("currencies") or {}).values())
        if len(cur) == 1:
            facts.append(["currency", lc(cur[0]["name"])])
        langs = [lc(v) for v in (c.get("languages") or {}).values()]
        if langs:
            facts.append(["official_languages", "; ".join(langs[:6])])
        dem = ((c.get("demonyms") or {}).get("eng") or {}).get("m")
        if dem:
            facts.append(["demonym", lc(dem)])
        idd = c.get("idd") or {}
        if idd.get("root") and len(idd.get("suffixes") or []) == 1:
            facts.append(["calling_code", idd["root"] + idd["suffixes"][0]])
        b = [cname[x] for x in c.get("borders") or [] if x in cname]
        facts.append(["borders", "; ".join(b) if b else "none"])
        facts.append(["landlocked", "yes" if c.get("landlocked") else "no"])
        if c.get("tld"):
            facts.append(["internet_domain", c["tld"][0]])
        d = ci.get(c["cca3"])
        recs_asof = {}
        if d and d.get("population"):
            facts.append(["population", num(d["population"]), 2015])
        al = [lc(c["name"]["official"])] + [lc(a) for a in c.get("altSpellings", []) if len(a) > 3]
        al = sorted(set(a for a in al if a and a != name and re.fullmatch(r"[a-z .'-]+", a)))
        emit({"key": "country:" + c["cca3"], "name": name, "aliases": al, "type": "country",
              "qual": "country", "facts": facts, "src": "mledoze-countries+countryinfo", "asof": None,
              "desc": "country in " + cont if cont else "country"})
    # ---------------- cities (and US states)
    states = gc.get_us_states()
    st_code = {k: lc(v["name"]) for k, v in states.items()}
    largest = {}
    for cid, c in cities.items():
        if c["countrycode"] == "US" and c["admin1code"] in st_code:
            s = st_code[c["admin1code"]]
            if s not in largest or c["population"] > largest[s][1]:
                largest[s] = (lc(c["name"]), c["population"])
    for cid, c in cities.items():
        name = lc(c["name"])
        if not re.fullmatch(r"[a-z0-9 .'-]+", name or ""):
            continue
        country = cc2name.get(c["countrycode"])
        if not country:
            continue
        facts = [["country", country]]
        qual = "city in " + country
        if c["countrycode"] == "US" and c["admin1code"] in st_code:
            facts.append(["state", st_code[c["admin1code"]]])
            qual = "city in " + st_code[c["admin1code"]]
        facts.append(["population", num(c["population"]), 2025])
        if (name, c["countrycode"]) in capital_of:
            facts.append(["capital_of", capital_of[(name, c["countrycode"])]])
        emit({"key": "city:%s" % cid, "name": name, "type": "city", "qual": qual, "facts": facts,
              "src": "geonamescache", "asof": None, "desc": qual, "citypop": c["population"]})
    for s in us.states.STATES:
        name = lc(s.name)
        facts = [["capital", lc(s.capital)], ["abbreviation", s.abbr.lower()], ["country", "united states"]]
        if s.statehood_year:
            facts.append(["statehood_year", str(s.statehood_year)])
        if name in largest:
            facts.append(["largest_city", largest[name][0]])
        emit({"key": "usstate:" + s.abbr, "name": name, "type": "us_state", "qual": "u.s. state",
              "facts": facts, "src": "us-package", "asof": None, "desc": "u.s. state", "aliases": [s.abbr.lower()]})
    # ---------------- elements
    ends = [2, 10, 18, 36, 54, 86, 118]
    cat = {}
    for z in (3, 11, 19, 37, 55, 87):
        cat[z] = "alkali metal"
    for z in (4, 12, 20, 38, 56, 88):
        cat[z] = "alkaline earth metal"
    for z in (2, 10, 18, 36, 54, 86, 118):
        cat[z] = "noble gas"
    for z in (9, 17, 35, 53, 85, 117):
        cat[z] = "halogen"
    for z in range(57, 72):
        cat[z] = "lanthanide"
    for z in range(89, 104):
        cat[z] = "actinide"
    for z in (5, 14, 32, 33, 51, 52):
        cat[z] = "metalloid"
    for z in (1, 6, 7, 8, 15, 16, 34):
        cat[z] = "nonmetal"
    for z in (13, 31, 49, 50, 81, 82, 83, 84, 113, 114, 115, 116):
        cat[z] = "post-transition metal"

    def period_group(z):
        p = next(i + 1 for i, e in enumerate(ends) if z <= e)
        start = ([0] + ends)[p - 1]
        k = z - start  # 1-based position in period
        if p == 1:
            g = 1 if z == 1 else 18
        elif p in (2, 3):
            g = k if k <= 2 else k + 10
        elif p in (4, 5):
            g = k
        else:
            if k <= 2:
                g = k
            elif k <= 17:
                g = None if not (k == 3) else 3
                if 3 < k <= 17:
                    g = None
            else:
                g = k - 14
        return p, g
    for el in periodictable.elements:
        if el.number < 1 or el.number > 118:
            continue
        z = el.number
        if z not in cat:
            cat[z] = "transition metal"
        p, g = period_group(z)
        name = el.name.lower()
        facts = [["symbol", el.symbol.lower()], ["atomic_number", str(z)], ["period", str(p)],
                 ["element_category", cat[z]]]
        if g:
            facts.append(["group", str(g)])
        if el.mass and z <= 103:
            facts.append(["atomic_mass", ("%.3f" % el.mass).rstrip("0").rstrip(".")])
        emit({"key": "element:%d" % z, "name": "aluminum" if name == "aluminum" else name, "type": "element",
              "qual": "chemical element", "facts": facts, "src": "periodictable", "asof": None,
              "desc": "chemical element", "aliases": ["aluminium"] if name == "aluminum" else []})
    # ---------------- planets (hand table)
    P = [("mercury", 1, "4,879 km", "0", "88 days", "59 earth days", "57.9 million km", "terrestrial planet"),
         ("venus", 2, "12,104 km", "0", "225 days", "243 earth days", "108.2 million km", "terrestrial planet"),
         ("earth", 3, "12,742 km", "1", "365.25 days", "24 hours", "149.6 million km", "terrestrial planet"),
         ("mars", 4, "6,779 km", "2", "687 days", "24.6 hours", "227.9 million km", "terrestrial planet"),
         ("jupiter", 5, "139,820 km", "95", "11.9 years", "9.9 hours", "778.5 million km", "gas giant"),
         ("saturn", 6, "116,460 km", "146", "29.4 years", "10.7 hours", "1,432 million km", "gas giant"),
         ("uranus", 7, "50,724 km", "27", "84 years", "17.2 hours", "2,867 million km", "ice giant"),
         ("neptune", 8, "49,244 km", "14", "164.8 years", "16.1 hours", "4,515 million km", "ice giant")]
    for name, order, dia, moons, yr, day, dist, typ in P:
        emit({"key": "planet:" + name, "name": name, "type": "planet", "qual": "planet", "desc": typ,
              "facts": [["planet_order", str(order)], ["diameter", dia], ["moons", moons, 2023], ["orbital_period", yr],
                        ["day_length", day], ["distance_from_sun", dist], ["planet_type", typ]],
              "src": "hand-planets", "asof": None, "pop": 10 ** 6})
    emit({"key": "planet:pluto", "name": "pluto", "type": "planet", "qual": "dwarf planet", "desc": "dwarf planet",
          "facts": [["diameter", "2,377 km"], ["moons", "5", 2023], ["orbital_period", "248 years"],
                    ["planet_type", "dwarf planet"]], "src": "hand-planets", "asof": None, "pop": 10 ** 6})
    # ---------------- airports
    ap = airportsdata.load("IATA")
    for code, a in ap.items():
        name = lc(a["name"])
        country = cc2name.get(a["country"])
        city = lc(a["city"])
        if not name or not country or not re.fullmatch(r"[a-z0-9 .'-]+", name):
            continue
        facts = [["iata_code", code.lower()], ["country", country]]
        if city and re.fullmatch(r"[a-z .'-]+", city):
            facts.append(["city", city])
        if a.get("elevation") not in (None, "") and float(a["elevation"]) > 0:
            facts.append(["elevation", num(float(a["elevation"])) + " feet"])
        emit({"key": "airport:" + code, "name": name, "type": "airport", "qual": "airport in " + (city or country),
              "facts": facts, "src": "airportsdata", "asof": None, "desc": "airport in " + (city or country),
              "aliases": [code.lower() + " airport"]})
    # ---------------- books
    with open(os.path.join(RAW, "goodbooks-10k", "books.csv")) as f:
        for r in csv.DictReader(f):
            title = lc(re.sub(r"\s*\([^)]*#\d+[^)]*\)\s*$", "", r["title"] or ""))
            orig = lc(r["original_title"] or "")
            if not title or not re.fullmatch(r"[a-z0-9 .,'&:-]+", title) or len(title.split()) > 9:
                continue
            book_al = [orig] if orig and orig != title and re.fullmatch(r"[a-z0-9 .,'&:-]+", orig) else []
            author = lc(r["authors"].split(",")[0])
            facts = [["author", author]]
            try:
                y = int(float(r["original_publication_year"]))
                if 1000 <= y <= 2017:
                    facts.append(["publication_year", str(y)])
            except ValueError:
                pass
            emit({"key": "book:" + r["book_id"], "name": title, "type": "book", "qual": "book by " + author,
                  "facts": facts, "src": "goodbooks-10k", "asof": None, "desc": "book by " + author, "aliases": book_al,
                  "pop": int(r["ratings_count"]) // 10})
    out.close()
    print(json.dumps(dict(sorted(stats.items())), indent=0)[:3000])


if __name__ == "__main__":
    main()
