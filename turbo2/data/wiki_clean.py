"""Pass 2: strip wiki markup (mwparserfromhell) from leads and plot sections.
Resumable: processes shards that have no output yet, with a process pool, and stops
before the time budget.  Usage: python3 wiki_clean.py SPLITDIR OUTDIR [budget_s]"""
import glob, gzip, json, os, re, sys, time
from multiprocessing import Pool
import mwparserfromhell as mw

NS_DROP = re.compile(r"^\s*:?\s*(file|image|category|media|wikipedia|wp|template|help|portal|s|wikt|commons)\s*:", re.I)
TAG_DROP = {"ref", "table", "gallery", "math", "timeline", "score", "imagemap", "syntaxhighlight", "source", "code",
            "references", "div", "blockquote", "poem", "chem", "ce", "hiero", "graph", "mapframe"}


UNITS = {"km": "kilometres", "mi": "miles", "m": "metres", "ft": "feet", "cm": "centimetres", "mm": "millimetres",
         "in": "inches", "km2": "square kilometres", "sqmi": "square miles", "sqkm": "square kilometres",
         "mi2": "square miles", "ha": "hectares", "acre": "acres", "kg": "kilograms", "lb": "pounds", "t": "tonnes",
         "g": "grams", "C": "degrees Celsius", "F": "degrees Fahrenheit", "K": "kelvin", "l": "litres", "L": "litres",
         "km/h": "kilometres per hour", "mph": "miles per hour", "m2": "square metres", "nmi": "nautical miles",
         "yd": "yards", "oz": "ounces", "st": "stone", "kW": "kilowatts", "hp": "horsepower", "MW": "megawatts",
         "au": "astronomical units", "AU": "astronomical units", "ly": "light-years"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
KEEP_FIRST = {"nowrap", "nobr", "small", "nobold", "abbr", "ill", "lang", "transl", "noitalic", "smallcaps",
              "sc", "big", "visible anchor", "vanchor", "em", "strong", "nowrap begin", "ubl"}


def pos_params(t):
    return [str(p.value).strip() for p in t.params if not p.showkey]


def render_template(t):
    name = str(t.name).strip().lower().replace("_", " ")
    ps = pos_params(t)
    try:
        if name in ("convert", "cvt") and ps:
            if len(ps) >= 4 and ps[1] in ("-", "to", "and", "–", "or"):
                return "%s to %s %s" % (ps[0], ps[2], UNITS.get(ps[3], ps[3]))
            if len(ps) >= 2:
                return "%s %s" % (ps[0], UNITS.get(ps[1], ps[1]))
        if name.startswith("lang-") and ps:
            return ps[0]
        if name == "lang" and len(ps) >= 2:
            return ps[1]
        if name in KEEP_FIRST and ps:
            return ps[0]
        if name in ("birth date", "death date", "birth date and age", "death date and age", "start date",
                    "dob", "bda", "dda", "end date", "film date") and len(ps) >= 3:
            y, m, d = [p for p in ps if p.isdigit()][:3] if sum(p.isdigit() for p in ps) >= 3 else (None,) * 3
            if y and 1 <= int(m) <= 12:
                return "%d %s %s" % (int(d), MONTHS[int(m) - 1], y)
        if name in ("circa", "c.") and ps:
            return "c. " + ps[0]
        if name == "as of" and ps:
            return "As of " + ps[0]
        if name in ("frac", "fraction") and len(ps) >= 2:
            return "%s/%s" % (ps[-2], ps[-1]) if len(ps) == 2 else "%s %s/%s" % (ps[0], ps[1], ps[2])
        if name in ("us$", "usd") and ps:
            return "US$" + ps[0]
        if name in ("sortname",) and len(ps) >= 2:
            return ps[0] + " " + ps[1]
        if name in ("mvar", "math", "val") and ps:
            return ps[0]
    except Exception:
        return None
    return None


def clean(text):
    i = text.find("\'\'\'")
    if i > 0:
        j = text.rfind("\n", 0, i)
        # only cut if what precedes is caption/infobox-like (keeps a normal lead intact)
        if j > 0:
            text = text[j + 1:]
    try:
        code = mw.parse(text)
    except Exception:
        return ""
    for t in code.filter_templates(recursive=False):
        r = render_template(t)
        try:
            if r is None:
                code.remove(t)
            else:
                code.replace(t, r)
        except ValueError:
            pass
    for l in code.filter_wikilinks():
        if NS_DROP.match(str(l.title)):
            try:
                code.remove(l)
            except ValueError:
                pass
    for tg in code.filter_tags():
        if str(tg.tag).lower().strip() in TAG_DROP:
            try:
                code.remove(tg)
            except ValueError:
                pass
    s = code.strip_code(normalize=True, collapse=True)
    s = re.sub(r"\{\|.*?\|\}", " ", s, flags=re.S)      # stray tables
    s = re.sub(r"<[^>]{0,200}>", " ", s)                 # stray html
    s = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", s)  # external links keep label
    s = re.sub(r"https?://\S+", " ", s)
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"\(\s*[;,:]*\s*\)", " ", s)              # empty parens left by templates
    s = re.sub(r"\(\s*[;,]\s*", "(", s)
    s = re.sub(r"\s*[;,]\s*\)", ")", s)
    s = re.sub(r"[ \t]+", " ", s)
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln and not ln.startswith(("|", "!", "{", "}", "*", "#", "=", ":", ";"))]
    s = "\n".join(lines)
    s = re.sub(r" ([,.;:])", r"\1", s)
    return s.strip()


def work(path_out):
    path, out = path_out
    n = 0
    tmp = out + ".tmp"
    with gzip.open(path, "rt") as fi, gzip.open(tmp, "wt", compresslevel=3) as fo:
        for line in fi:
            r = json.loads(line)
            lead = clean(r["lead"])
            plots = [clean(p) for p in r["plots"]]
            plots = [p for p in plots if len(p) > 200]
            fo.write(json.dumps({"t": r["t"], "lead": lead, "plots": plots, "nsec": r["nsec"], "len": r["len"]}) + "\n")
            n += 1
    os.replace(tmp, out)
    return n


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    budget = float(sys.argv[3]) if len(sys.argv) > 3 else 520
    os.makedirs(dst, exist_ok=True)
    jobs = []
    for p in sorted(glob.glob(os.path.join(src, "shard_*.jsonl.gz"))):
        o = os.path.join(dst, os.path.basename(p))
        if not os.path.exists(o):
            jobs.append((p, o))
    t0 = time.time()
    print("todo", len(jobs), flush=True)
    with Pool(4) as pool:
        it = pool.imap_unordered(work, jobs)
        done = 0
        for n in it:
            done += 1
            print("shard done", n, "elapsed", round(time.time() - t0), flush=True)
            if time.time() - t0 > budget:
                pool.terminate()
                break
    left = sum(1 for p, o in jobs if not os.path.exists(o))
    print("remaining", left)
