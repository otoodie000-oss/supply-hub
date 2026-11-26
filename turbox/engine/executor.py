"""TurboX executor: the non-learned parts that run the model's actions (Python twin of the Scratch engine).
It reads the exact lists shipped in the .sb3 (WORK/kb/lists.json) so both sides behave identically.

  find(tokens)      candidate index: exact name -> alias -> 'the'-stripped -> word postings (fuzzy-corrected
                    words); returns up to 3 entity ids ordered by (match quality, prior bucket, id)
  render_cands      '<c1> name <d> descriptor ...' tokens (descriptor = stored description or type phrase)
  value(id, rel)    stored value rendered as tokens (+ as-of year for time-sensitive relations) and the
                    referenced entity id for chained lookups
  tools             2.0's helpers (twins) + cmp_more/cmp_less/isa/years_between/count_items over values the
                    model looked up.  The executor never chooses an answer: it returns what was asked for."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("..", "../kb", "../helpers", "../common"):
    sys.path.insert(0, os.path.join(HERE, p))
from relations import REL  # noqa: E402
import twins  # noqa: E402
from tok import split  # noqa: E402
from render import MONTHS, group  # noqa: E402
from vocab import SID, REL_OF_TOK, TOK_OF_REL, TOOL_OF_TOK  # noqa: E402

LISTS = "/home/user/work/x/kb/lists.json"
CODE2REL = {REL[r][0]: r for r in REL}
TYPE_PHRASE = {"c": "city", "n": "country", "s": "u.s. state", "e": "chemical element", "l": "planet",
               "a": "airport", "b": "book", "o": "word", "v": "verb", "j": "adjective", "p": "person", "w": "thing"}
STOPW = {"the", "of", "a", "an", "and", "in", "on", "at", "de", "la", "le", "du", "von", "van", "der", "for", "to"}
NUMLIKE = re.compile(r"^\s*[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?\s*$|^\s*0x[0-9a-f]+\s*$|^\s*0b[01]+\s*$|^\s*0o[0-7]+\s*$")


def skey(s):
    return "#" + s if (s.strip() and NUMLIKE.match(s)) or s.strip() in ("infinity", "-infinity", "+infinity") else s


def bounded_edit(a, b, k):
    """Optimal-string-alignment distance (insert/delete/substitute/adjacent swap) if <= k else k+1.
    Plain full DP over the two short words (same algorithm in Scratch)."""
    if abs(len(a) - len(b)) > k:
        return k + 1
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            v = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, d[i - 2][j - 2] + 1)
            d[i][j] = v
    return d[n][m] if d[n][m] <= k else k + 1


class Executor:
    def __init__(self, path=LISTS):
        L = json.load(open(path))
        self.names, self.recs = L["E_NAME"], L["E_REC"]
        self.akey, self.aid = L["A_KEY"], L["A_ID"]
        self.words, self.post = L["WORDS"], L["POST"]
        self.lstart = L["LSTART"]
        self._rec_cache = {}

    # ------------------------------------------------------------ sorted-list search (1-based like Scratch)
    @staticmethod
    def lower_bound(lst, key):
        lo, hi = 1, len(lst)
        while lo <= hi:
            mid = (lo + hi) // 2
            if lst[mid - 1] < key:
                lo = mid + 1
            else:
                hi = mid - 1
        return lo

    def equal_range(self, lst, key, cap=50):
        i = self.lower_bound(lst, key)
        out = []
        while i <= len(lst) and lst[i - 1] == key and len(out) < cap:
            out.append(i)
            i += 1
        return out

    # ------------------------------------------------------------ records
    def rec(self, eid):
        r = self._rec_cache.get(eid)
        if r is None:
            s = self.recs[eid - 1]
            head, body = s.split("|", 1)
            facts = []
            for part in body.split("~") if body else []:
                code, rest = part[:2], part[2:]
                src = None
                if "`" in rest:
                    rest, src = rest.split("`", 1)
                asof = None
                if "^" in rest:
                    rest, a = rest.rsplit("^", 1)
                    asof = int(a)
                facts.append((CODE2REL.get(code), rest, asof, src))
            r = {"type": head[0], "src": head[1], "prior": int(head[2]), "facts": facts}
            self._rec_cache[eid] = r
        return r

    def name_tokens(self, eid):
        n = self.names[eid - 1]
        return (n[1:] if n.startswith("#") else n).split(" ")

    def fact(self, eid, rel):
        for f in self.rec(eid)["facts"]:
            if f[0] == rel:
                return f
        return None

    # ------------------------------------------------------------ candidate index
    def find(self, toks):
        toks = [t for t in toks if t]
        if not toks:
            return []
        key = " ".join(toks)
        tried = [key]
        if toks[0] == "the" and len(toks) > 1:
            tried.append(" ".join(toks[1:]))
        for k in tried:
            ids = self.equal_range(self.names, skey(k))
            ids += [self.aid[i - 1] for i in self.equal_range(self.akey, skey(k))]
            if ids:
                return self._order(ids, exact=True)
        # word postings with fuzzy-corrected words
        counts = {}
        qwords = [t for t in toks if t[:1].isalpha() and t not in STOPW]
        for w in qwords:
            j = self.lower_bound(self.words, skey(w))
            wid = j if j <= len(self.words) and self.words[j - 1] == w else self.fuzzy(w)
            if not wid:
                continue
            prev = 0
            for d in self.post[wid - 1].split(" "):
                prev += int(d)
                counts[prev] = counts.get(prev, 0) + 1
        if not counts:
            return []
        need = max(1, (len(qwords) + 1) // 2)
        cands = [e for e, c in counts.items() if c >= need]
        cands.sort(key=lambda e: (-counts[e], -self.rec(e)["prior"], e))
        return cands[:3]

    def _order(self, ids, exact):
        seen = []
        for i in ids:
            if i not in seen:
                seen.append(i)
        seen.sort(key=lambda e: (-self.rec(e)["prior"], e))
        return seen[:3]

    def fuzzy(self, w):
        """best WORDS entry with the same first letter within edit distance 1 (2 for words of 8+ letters)."""
        c = w[0]
        if not ("a" <= c <= "z"):
            return 0
        k = 2 if len(w) >= 8 else 1
        lo = self.lstart[ord(c) - 97]
        hi = self.lstart[ord(c) - 96] - 1 if c != "z" else len(self.words)
        best, bd, bn = 0, k + 1, 0
        for i in range(lo, hi + 1):
            cand = self.words[i - 1]
            if abs(len(cand) - len(w)) > k:
                continue
            d = bounded_edit(w, cand, k)
            if d <= k:
                npost = self.post[i - 1].count(" ") + 1
                if d < bd or (d == bd and npost > bn):
                    best, bd, bn = i, d, npost
        return best if bd <= k else 0

    # ------------------------------------------------------------ rendering
    def describe(self, eid):
        """short descriptor tokens shown with a candidate (<= 6 tokens)"""
        r = self.rec(eid)
        d = self.fact(eid, "description")
        if d:
            t = split(d[1])[:6]
            while len(t) > 1 and t[-1] in STOPW:
                t = t[:-1]
            return t
        t = r["type"]
        if t == "c":
            st = self.fact(eid, "state") or self.fact(eid, "country")
            if st and st[1].startswith("@"):
                return ["city", "in"] + self.name_tokens(int(st[1][1:]))[:4]
        if t == "a":
            c = self.fact(eid, "city")
            if c:
                return ["airport", "in"] + split(c[1])[:4]
        if t == "b":
            a = self.fact(eid, "author")
            if a:
                return ["book", "by"] + split(a[1])[:4]
        if t == "p":
            for rel in ("occupation", "position", "nationality"):
                f = self.fact(eid, rel)
                if f:
                    return (["person", ","] + split(f[1]))[:6]
            return ["person"]
        return [TYPE_PHRASE.get(t, "thing")]

    def render_cands(self, ids):
        if not ids:
            return [("<none>", "<none>")]
        out = []
        for k, e in enumerate(ids):
            out.append(("<c%d>" % (k + 1), "<c%d>" % (k + 1)))
            out += [(None, t) for t in self.name_tokens(e)]
            out.append(("<d>", "<d>"))
            out += [(None, t) for t in self.describe(e)]
        return out

    def render_value(self, rel, v):
        kind = REL[rel][1]
        if v.startswith("@"):
            return self.name_tokens(int(v[1:])), int(v[1:])
        if kind == "date" and re.fullmatch(r"\d{8}", v):
            return [MONTHS[int(v[4:6]) - 1], str(int(v[6:])), ",", str(int(v[:4]))], None
        if kind in ("date", "year") and re.fullmatch(r"\d{3,4}", v):
            return [str(int(v))], None
        if kind == "number":
            m = re.match(r"^(-?\d+)(\.\d+)?(.*)$", v)
            if m:
                return [group(m.group(1)) + (m.group(2) or "")] + split(m.group(3)), None
        if kind == "list":
            items = [x.strip() for x in v.split(";") if x.strip()]
            out = []
            for i, it in enumerate(items):
                if i:
                    out.append("and" if i == len(items) - 1 else ",")
                out += split(it)
            return out, None
        return split(v), None

    def value(self, eid, rel):
        """-> (tokens incl. markers, ref_id or None, found)"""
        f = self.fact(eid, rel)
        if not f:
            return [("<nov>", "<nov>")], None, False
        toks, ref = self.render_value(rel, f[1])
        out = [("<v>", "<v>")] + [(None, t) for t in toks]
        if REL[rel][2] and f[2]:
            out += [("<asof>", "<asof>"), (None, str(f[2]))]
        return out, ref, True

    # ------------------------------------------------------------ TurboX tools over looked-up values
    def isa(self, child, parent):
        cur = child
        for _ in range(20):
            f = self.fact(cur, "is_a")
            if not f or not f[1].startswith("@"):
                return False
            cur = int(f[1][1:])
            if cur == parent:
                return True
        return False


def num_of(tokens):
    for t in tokens:
        if t[:1].isdigit():
            try:
                return float(t.replace(",", ""))
            except ValueError:
                pass
    return None
