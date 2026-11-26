"""TurboX special tokens (actions, relations, tools, arguments).  Word vocabularies are built from data
(engine/build_vocab.py).  Token ids: specials first, then input words."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kb"))
sys.path.insert(0, os.path.join(HERE, "..", "helpers"))
from relations import REL  # noqa: E402
import twins  # noqa: E402

BASE = ["<pad>", "<unk>", "<num>", "<bos>", "<q>", "<h>", "<ctx>", "<find>", "</find>", "<c1>", "<c2>", "<c3>", "<d>",
        "<none>", "<pick1>", "<pick2>", "<pick3>", "<v>", "<nov>", "<asof>", "<tool>", "</tool>", "<r>", "<say_ans>",
        "<say_fb>", "<say_cq>", "<say_open>", "<end>", "<mem>", "<first>", "<second>", "<yes>", "<no>", "<sep>",
        "<err>", "<more>"]
RELS = sorted(REL)
REL_TOK = ["<r_%s>" % r.replace(" ", "_").replace("'", "") for r in RELS]
TOOLS = ["time", "date", "weekday", "days_until", "days_since", "date_add", "age", "leap", "week", "world_time",
         "holiday", "timer", "calc", "pct_of", "pct_is", "pct_change", "tip", "discount", "convert", "prime", "factors",
         "gcd", "lcm", "roman", "words", "coin", "dice", "rand", "pick", "sort", "count_letter", "count_letters",
         "count_words", "spell", "reverse",
         # TurboX additions (executor over stored facts / text store)
         "cmp_more", "cmp_less", "isa", "years_between", "count_items", "joke", "story", "advice", "explain"]
TOOL_TOK = ["<t_%s>" % t for t in TOOLS]
MONTH_TOK = ["<mo_%d>" % m for m in range(1, 13)]
UNIT_TOK = ["<u_%s>" % u for u in sorted(twins.UNITS)]
HOLIDAY_TOK = ["<h_%s>" % h for h in twins.HOLIDAY_NAMES]
MEM_SLOTS = ["name", "city", "pet", "food", "job", "color", "age", "birthday", "sport", "friend", "school", "hobby"]
MEM_TOK = ["<ms_%s>" % s for s in MEM_SLOTS]
OPS = ["<op_plus>", "<op_minus>", "<op_times>", "<op_div>", "<op_pow>", "<op_lp>", "<op_rp>", "<op_mod>", "<days>",
       "<weeks>", "<months>", "<years>", "<24h>"]
SPECIALS = BASE + REL_TOK + TOOL_TOK + MONTH_TOK + UNIT_TOK + HOLIDAY_TOK + MEM_TOK + OPS
assert len(SPECIALS) == len(set(SPECIALS))
SID = {s: i for i, s in enumerate(SPECIALS)}
REL_OF_TOK = {t: r for t, r in zip(REL_TOK, RELS)}
TOK_OF_REL = {r: t for t, r in zip(REL_TOK, RELS)}
TOOL_OF_TOK = {t: n for t, n in zip(TOOL_TOK, TOOLS)}

if __name__ == "__main__":
    print(len(SPECIALS), len(REL_TOK), len(TOOL_TOK), len(UNIT_TOK), len(HOLIDAY_TOK))
