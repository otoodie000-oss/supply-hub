"""Fact storage rendering: how a stored value is shown as evidence text (and in gold answers).
Non-learned presentation only (dates, digit grouping); it never picks an answer."""
import re

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def group(n):
    """'66078000' -> '66,078,000' (integer part only)"""
    s = str(n)
    neg = s.startswith("-")
    s = s.lstrip("-")
    out = ""
    while len(s) > 3:
        out = "," + s[-3:] + out
        s = s[:-3]
    return ("-" if neg else "") + s + out


def render_date(v):
    """'18790314' or '1879-03-14' -> 'march 14, 1879'; '1879' -> '1879'; '0705' -> '705'"""
    d = v.replace("-", "")
    if re.fullmatch(r"\d{8}", d):
        y, m, dd = int(d[:4]), int(d[4:6]), int(d[6:])
        return "%s %d, %d" % (MONTHS[m - 1], dd, y)
    if re.fullmatch(r"\d{3,4}", d):
        return str(int(d))
    return v


def render_number(v):
    """'66078000' -> '66,078,000'; '551695 square kilometres' -> '551,695 square kilometres'; decimals kept."""
    m = re.match(r"^(-?\d+)(\.\d+)?(.*)$", v)
    if not m:
        return v
    return group(m.group(1)) + (m.group(2) or "") + m.group(3)


def render(kind, v):
    if kind == "date":
        return render_date(v)
    if kind == "number":
        return render_number(v)
    if kind == "list":
        items = [x.strip() for x in v.split(";") if x.strip()]
        if len(items) <= 1:
            return v
        return ", ".join(items[:-1]) + " and " + items[-1]
    return v


def number_value(v):
    """float value of a stored number/date-year string ('66,078,000 people' -> 66078000.0)"""
    m = re.match(r"^\s*(-?[\d,]+(?:\.\d+)?)", v)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))
