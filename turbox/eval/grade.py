"""Automatic grader for the TurboX 1M test (same rules for Turbo 2.0 and TurboX replies).

Reply form (decided from the text alone):
  bare_idk   a decline with no useful content ("I don't know", "not sure", "I can't answer that")
  fallback   says the exact answer isn't in its offline knowledge / it can't check, then gives something
             concrete (>= 3 new content words, a number, or a specific question back)
  clarify    a question back to the user (one '?' sentence that names options or asks for a specific detail)
  answer     anything else that states content
  nonanswer  chat with no factual content (e.g. "Nice!")
Grade (final turn only):
  correct            matches the item's mode: answer items -> gold found in the first two sentences, as-of year
                     present for time-sensitive facts, no unverifiable number; fallback items -> proper fallback
                     (or the right answer); clarify items -> clarifying question; ambiguous -> clarify naming
                     >=2 readings, or the likeliest reading answered and named
  confidently_wrong  an answer-form reply that is not correct (states something other than the gold as fact),
                     or any answer-form reply to an unknowable/underspecified question
  fallback           proper fallback on an item whose mode required an answer
  bare_idk           decline with no content (any item)
  clarify_wrong      a clarifying question where an answer was required
  nonanswer          no factual content and no decline
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from textnorm import clean_text  # noqa: E402
from render import MONTHS  # noqa: E402

DECLINE = re.compile(r"\b(i don'?t know|i do not know|not sure|no idea|i can'?t (answer|tell|say|check|look|see|access)|"
                     r"i cannot|don'?t have (that|this|a note|any|the exact|access)|isn'?t in my|is not in my|"
                     r"not in my (offline|notes|knowledge|data)|offline knowledge|can'?t check|unable to|i'm sorry, i can'?t|"
                     r"don'?t have live|no live|i have no way|can'?t know|i'm not able|beyond what i know|"
                     r"not something i (know|can)|i don'?t have information)\b")
STOP = set("""the a an of in on at to for from with by and or but is are was were be been it its this that these those
i you he she they we me my your his her their our them us what who where when why how which whose do does did done
can could would should will shall may might must have has had not no yes so as if then than there here about into
over under just only also very really any some all each every more most much many such own same other another out up
down off again further once please tell know think say said like well okay ok hi hello hey thanks thank sure here's
that's it's i'm don't can't isn't""".split())
NUMWORD = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
FILLER = set("""notes note one offline knowledge exact figure answer information related something here's find sorry fact
facts thing things record records data way check live access look up able currently right now today able time
anything else help instead what i do know closest verified can tell share""".split())


def norm(s):
    s = clean_text(s or "").lower()
    s = s.replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def words(s):
    return re.findall(r"[a-z0-9']+", norm(s))


def content(s):
    return [w for w in words(s) if w not in STOP and len(w) > 1]


def sentences(s):
    parts = re.split(r"(?<=[.!?])\s+", norm(s))
    return [p for p in parts if p]


def first2(s):
    return " ".join(sentences(s)[:2])


def numbers(s):
    """all numbers in text, with 'million' style scaling; returns list of floats"""
    out = []
    t = norm(s)
    for m in re.finditer(r"(-?\d[\d,]*(?:\.\d+)?)\s*(thousand|million|billion|trillion)?", t):
        raw = m.group(1).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        if m.group(2):
            v *= NUMWORD[m.group(2)]
        out.append(v)
    return out


def has_phrase(text, phrase):
    p = norm(phrase)
    if not p:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", norm(text)) is not None


def form_of(reply, question):
    r = norm(reply)
    if not r:
        return "nonanswer"
    dec = bool(DECLINE.search(r))
    qw = set(content(question))
    rest = DECLINE.sub(" ", r)
    new = [w for w in content(rest) if w not in qw and w not in FILLER]
    concrete = len(new) >= 3 or bool(re.search(r"\d", rest)) or ("?" in rest and len(new) >= 1)
    if dec:
        return "fallback" if concrete else "bare_idk"
    if r.rstrip().endswith("?") or (len(sentences(r)) <= 2 and "?" in r and re.match(r"^(do|did|are|is|which|what|who|could|can|would)\b", sentences(r)[-1])):
        return "clarify"
    if not new and not re.search(r"\d", r):
        return "nonanswer"
    return "answer"


def match_gold(g, reply, question=""):
    t = g.get("type")
    f2 = first2(reply)
    if t == "text":
        ok = any(has_phrase(f2, a) for a in g["answers"])
    elif t == "text_all":
        ok = all(has_phrase(reply, a) for a in g["answers"])
    elif t == "year":
        ok = any(abs(v - g["y"]) < 0.5 for v in numbers(f2))
    elif t == "date":
        ns = numbers(f2)
        mon = MONTHS[g["m"] - 1]
        ok = any(abs(v - g["y"]) < 0.5 for v in ns) and (has_phrase(f2, mon) or has_phrase(f2, mon[:3])) and \
            any(abs(v - g["d"]) < 0.5 for v in ns)
        if not ok and re.search(r"\b%04d-%02d-%02d\b" % (g["y"], g["m"], g["d"]), f2):
            ok = True
    elif t == "number":
        tol = max(g.get("tol", 0.0), 1e-9)
        x = g["value"]
        ok = any(abs(v - x) <= tol * max(1.0, abs(x)) + 1e-9 for v in numbers(f2))
    elif t == "list":
        items = g["items"]
        hit = sum(1 for a in items if has_phrase(reply, a))
        ok = hit >= min(len(items), 5)
    elif t == "desc":
        gw = [w for w in content(g["text"])]
        if not gw:
            ok = False
        else:
            rw = set(content(reply))
            rec = sum(1 for w in gw if w in rw) / len(gw)
            ok = rec >= 0.6 and gw[-1] in rw
    elif t == "choice":
        r = norm(f2)
        pos = [r.find(norm(a)) for a in g["answer"] if norm(a) and r.find(norm(a)) >= 0]
        if not pos:
            ok = False
        else:
            p = min(pos)
            lo = [r.find(norm(o)) for o in g["other"] if r.find(norm(o)) >= 0]
            ok = not lo or p < min(lo) or any(("than " + norm(o)) in r for o in g["other"])
    elif t == "yesno":
        r = norm(f2)
        if g["answer"] == "yes":
            ok = bool(re.match(r"^(yes|yeah|yep|correct|true|it is|that's right)\b", r)) or (" is a " in r and " not " not in r and not r.startswith("no"))
        else:
            ok = bool(re.match(r"^(no|nope|not|false)\b", r)) or bool(re.search(r"\b(is not|isn't|is no|not a)\b", r))
    elif t == "tool":
        res = norm(g["result"])
        rn = numbers(res)
        if rn:
            got = numbers(reply)
            ok = all(any(abs(v - x) <= max(0.006, 0.0005 * abs(x)) for v in got) for x in rn)
            rw = [w for w in re.findall(r"[a-z]+", res) if w not in STOP and w not in ("tip", "total", "an", "increase", "decrease",
                                                                                      "days", "day", "yes", "no", "prime", "leap", "year")]
            if ok and rw:
                ok = sum(1 for w in rw if has_phrase(reply, w)) >= max(1, len(rw) // 2)
        else:
            rw = [w for w in re.findall(r"[a-z]+", res) if w not in STOP]
            ok = all(has_phrase(reply, w) for w in rw) if rw else False
            if res.startswith(("yes", "no")):
                ok = norm(reply).startswith(res.split(",")[0])
        if ok and ("increase" in res or "decrease" in res):
            ok = ("increase" in res) == ("increas" in norm(reply) or "up" in words(reply) or "grew" in norm(reply))
    elif t == "random":
        ok = any(has_phrase(reply, v) for v in g["valid"])
    else:
        ok = False
    if ok and g.get("asof"):
        ok = any(abs(v - g["asof"]) < 0.5 for v in numbers(reply))
    return ok


def extra_numbers_ok(reply, item, allowed_extra=()):
    """every number in an answer reply must come from the question, the gold, the as-of year or the evidence
    values the item's gold was built from (no invented figures)."""
    allowed = set()
    for t in item["turns"]:
        allowed.update(numbers(t))
    g = item["gold"]
    for k in ("value", "y", "m", "d", "asof"):
        if isinstance(g.get(k), (int, float)):
            allowed.add(float(g[k]))
    for k in ("text", "result"):
        if isinstance(g.get(k), str):
            allowed.update(numbers(g[k]))
    if g.get("type") == "ambiguous":
        lg = g["likeliest_gold"]
        for k in ("value", "y", "m", "d", "asof"):
            if isinstance(lg.get(k), (int, float)):
                allowed.add(float(lg[k]))
        if isinstance(lg.get("text"), str):
            allowed.update(numbers(lg["text"]))
    allowed.update(allowed_extra)
    for v in numbers(reply):
        if not any(abs(v - a) <= max(0.51, 0.011 * abs(a)) for a in allowed):
            return False
    return True


def supported(reply, question, support):
    """A fallback's concrete content must come from the system's own retrieved evidence for this turn
    (2.0: its retrieved fact texts; TurboX: its evidence values), or be a question back to the user."""
    r = norm(reply)
    rest = DECLINE.sub(" ", r)
    segs = [x for x in re.split(r"(?<=[.!?])\s+", rest) if x.strip()]
    stmt = " ".join(x for x in segs if not x.strip().endswith("?"))
    qw = set(content(question))
    need = [w for w in content(stmt) if w not in qw and w not in FILLER]
    if not need:
        return True
    have = set(content(support))
    return sum(1 for w in need if w in have) >= 0.8 * len(need)


def grade(item, reply, trace_numbers=(), support=""):
    """item: test item; reply: final-turn reply text; trace_numbers: numbers present in the system's own
    evidence for this turn -- allowed as extra figures because they are verified KB values; support: the
    system's retrieved evidence text for this turn (used to verify a fallback's concrete content)."""
    q = item["turns"][-1]
    form = form_of(reply, q)
    if form == "fallback" and not supported(reply, q, support):
        form = "fallback_unsupported"
    mode = item["mode"]
    g = item["gold"]
    if form == "bare_idk":
        return "bare_idk", form
    if form == "fallback_unsupported":
        return "confidently_wrong", form
    if mode == "answer":
        if form == "answer":
            if match_gold(g, reply, q) and extra_numbers_ok(reply, item, trace_numbers):
                return "correct", form
            return "confidently_wrong", form
        if form == "fallback":
            return "fallback", form
        if form == "clarify":
            return "clarify_wrong", form
        return "nonanswer", form
    if mode in ("fallback", "either"):
        if form == "fallback":
            if g.get("type") not in (None, "none") and match_gold(g, reply, q):
                return "correct", form
            return ("correct" if extra_numbers_ok(reply, item, trace_numbers) else "confidently_wrong"), form
        if form == "answer":
            if g.get("type") not in (None, "none") and match_gold(g, reply, q) and extra_numbers_ok(reply, item, trace_numbers):
                return "correct", form
            return "confidently_wrong", form
        if form == "clarify":
            return ("correct" if g.get("type") in (None, "none") else "clarify_wrong"), form
        return "nonanswer", form
    if mode == "clarify":
        if form == "clarify":
            return "correct", form
        if form == "answer":
            return "confidently_wrong", form
        if form == "fallback":
            return "fallback", form
        return "nonanswer", form
    if mode == "clarify_or_likeliest":
        cands = g["candidates"]
        if form == "clarify":
            named = 0
            r = set(content(reply))
            for key, desc in cands:
                dw = [w for w in content(desc) if w not in set(content(q))]
                if dw and sum(1 for w in dw if w in r) >= max(1, len(dw) // 2):
                    named += 1
            return ("correct" if named >= 2 else "clarify_wrong"), form
        if form in ("answer", "fallback"):
            dw = [w for w in content(g["likeliest_desc"]) if w not in set(content(q))]
            named = not dw or any(w in set(content(reply)) for w in dw)
            if match_gold(g["likeliest_gold"], reply, q) and named and extra_numbers_ok(reply, item, trace_numbers):
                return "correct", form
            return ("confidently_wrong" if form == "answer" else "fallback"), form
        return "nonanswer", form
    return "nonanswer", form
