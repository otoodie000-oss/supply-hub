"""A tiny DSL that emits Scratch 3 project.json blocks.

Serialisation rules enforced here (they broke earlier builds):
  * reporter in an input slot  -> [3, blockId, [shadowType, default]]
  * literal                    -> [1, [4|7|10, "value"]]
  * boolean / substack         -> [2, blockId]
  * parent/next links consistent, ids unique, top-level blocks have x/y
  * procedures_prototype / procedures_call share proccode + argumentids
Variables and lists are always declared on the Stage (global) and referenced by id.
"""
import json

NUM, POS, WHOLE, INT, TEXT, BCAST = 4, 5, 6, 7, 10, 11


class Expr:
    pass


class Lit(Expr):
    def __init__(self, v):
        self.v = v


class Blk(Expr):
    def __init__(self, opcode, inputs=None, fields=None, boolean=False, mutation=None):
        self.opcode = opcode
        self.inputs = inputs or {}  # name -> (expr, shadowType)
        self.fields = fields or {}
        self.boolean = boolean
        self.mutation = mutation


def lit_str(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        r = repr(v)
        return r
    return str(v)


class Project:
    def __init__(self):
        self.vars = {}  # name -> (id, value)
        self.lists = {}  # name -> (id, values)
        self.broadcasts = {}  # name -> id
        self.procs = {}  # name -> dict(proccode, argids, argnames, warp)
        self.targets_blocks = {}  # target name -> dict
        self._n = 0
        self._y = {}

    # ---------- declarations ----------
    def var(self, name, value=0):
        if name not in self.vars:
            self.vars[name] = ("v_" + name, value)
        return name

    def lst(self, name, values=None):
        if name not in self.lists:
            self.lists[name] = ("l_" + name, list(values or []))
        elif values is not None:
            self.lists[name] = (self.lists[name][0], list(values))
        return name

    def bcast(self, name):
        if name not in self.broadcasts:
            self.broadcasts[name] = "b_" + name.replace(" ", "_")
        return name

    def nid(self, tag="b"):
        self._n += 1
        return "%s%d" % (tag, self._n)

    # ---------- emission ----------
    def _emit_block(self, B, blk, parent):
        bid = self.nid()
        d = {"opcode": blk.opcode, "next": None, "parent": parent, "inputs": {}, "fields": {},
             "shadow": False, "topLevel": False}
        B[bid] = d
        for k, (e, st) in blk.inputs.items():
            d["inputs"][k] = self._emit_input(B, e, st, bid)
        d["fields"] = dict(blk.fields)
        if blk.mutation is not None:
            d["mutation"] = blk.mutation
        return bid

    def _emit_input(self, B, e, st, parent):
        if isinstance(e, (int, float, str)) and not isinstance(e, bool):
            e = Lit(e)
        if isinstance(e, Lit):
            if st == BCAST:
                return [1, [BCAST, e.v, self.broadcasts[e.v]]]
            return [1, [st, lit_str(e.v)]]
        if isinstance(e, Blk):
            bid = self._emit_block(B, e, parent)
            if e.boolean:
                return [2, bid]
            return [3, bid, [st, "" if st == TEXT else "0"]]
        if isinstance(e, list):  # substack
            first = self._emit_stack(B, e, parent)
            return [2, first] if first else None
        raise TypeError(e)

    def _emit_stack(self, B, stmts, parent):
        """Emit a list of statement Blks, chain via next/parent; return first id."""
        first, prev = None, None
        for s in stmts:
            if s is None:
                continue
            assert isinstance(s, Blk), s
            bid = self._emit_block(B, s, prev if prev else parent)
            if prev:
                B[prev]["next"] = bid
            else:
                first = bid
            prev = bid
        return first

    def _blocks(self, target):
        return self.targets_blocks.setdefault(target, {})

    def _place(self, target, bid, height):
        y = self._y.get(target, 0)
        B = self._blocks(target)
        B[bid]["topLevel"] = True
        B[bid]["x"] = 0
        B[bid]["y"] = y
        self._y[target] = y + 40 + height

    def script(self, target, hat, stmts):
        B = self._blocks(target)
        hid = self._emit_block(B, hat, None)
        first = self._emit_stack(B, stmts, hid)
        B[hid]["next"] = first
        self._place(target, hid, 40 * len(stmts))
        return hid

    def define(self, target, name, argnames, body, warp=True):
        """Custom block definition 'name %s %s ...' with run-without-screen-refresh."""
        B = self._blocks(target)
        argids = ["a_%s_%s" % (name, a) for a in argnames]
        proccode = name + "".join(" %s" for _ in argnames)
        self.procs[name] = {"proccode": proccode, "argids": argids, "argnames": argnames, "warp": warp}
        did = self.nid("d")
        pid = self.nid("p")
        B[did] = {"opcode": "procedures_definition", "next": None, "parent": None,
                  "inputs": {"custom_block": [1, pid]}, "fields": {}, "shadow": False, "topLevel": True}
        proto = {"opcode": "procedures_prototype", "next": None, "parent": did, "inputs": {}, "fields": {},
                 "shadow": True, "topLevel": False,
                 "mutation": {"tagName": "mutation", "children": [], "proccode": proccode,
                              "argumentids": json.dumps(argids), "argumentnames": json.dumps(argnames),
                              "argumentdefaults": json.dumps(["" for _ in argnames]),
                              "warp": "true" if warp else "false"}}
        B[pid] = proto
        for aid, an in zip(argids, argnames):
            sid = self.nid("s")
            B[sid] = {"opcode": "argument_reporter_string_number", "next": None, "parent": pid,
                      "inputs": {}, "fields": {"VALUE": [an, None]}, "shadow": True, "topLevel": False}
            proto["inputs"][aid] = [1, sid]
        first = self._emit_stack(B, body, did)
        B[did]["next"] = first
        self._place(target, did, 60)
        return did

    # ---------- reference helpers used by programs ----------
    def V(self, name):
        vid = self.vars[name][0]
        return Blk("data_variable", fields={"VARIABLE": [name, vid]})

    def L(self, name):
        return [name, self.lists[name][0]]


# ---------------- expression / statement constructors ----------------
def _n(x):
    return x


def add(a, b): return Blk("operator_add", {"NUM1": (a, NUM), "NUM2": (b, NUM)})
def sub(a, b): return Blk("operator_subtract", {"NUM1": (a, NUM), "NUM2": (b, NUM)})
def mul(a, b): return Blk("operator_multiply", {"NUM1": (a, NUM), "NUM2": (b, NUM)})
def div(a, b): return Blk("operator_divide", {"NUM1": (a, NUM), "NUM2": (b, NUM)})
def mod(a, b): return Blk("operator_mod", {"NUM1": (a, NUM), "NUM2": (b, NUM)})
def mathop(op, a): return Blk("operator_mathop", {"NUM": (a, NUM)}, {"OPERATOR": [op, None]})
def exp_(a): return mathop("e ^", a)
def sqrt_(a): return mathop("sqrt", a)
def round_(a): return Blk("operator_round", {"NUM": (a, NUM)})
def join(a, b): return Blk("operator_join", {"STRING1": (a, TEXT), "STRING2": (b, TEXT)})
def letter(i, s): return Blk("operator_letter_of", {"LETTER": (i, WHOLE), "STRING": (s, TEXT)})
def strlen(s): return Blk("operator_length", {"STRING": (s, TEXT)})
def lt(a, b): return Blk("operator_lt", {"OPERAND1": (a, TEXT), "OPERAND2": (b, TEXT)}, boolean=True)
def gt(a, b): return Blk("operator_gt", {"OPERAND1": (a, TEXT), "OPERAND2": (b, TEXT)}, boolean=True)
def eq(a, b): return Blk("operator_equals", {"OPERAND1": (a, TEXT), "OPERAND2": (b, TEXT)}, boolean=True)
def and_(a, b): return Blk("operator_and", {"OPERAND1": (a, None), "OPERAND2": (b, None)}, boolean=True)
def or_(a, b): return Blk("operator_or", {"OPERAND1": (a, None), "OPERAND2": (b, None)}, boolean=True)
def not_(a): return Blk("operator_not", {"OPERAND": (a, None)}, boolean=True)
def answer(): return Blk("sensing_answer")
def arg(name): return Blk("argument_reporter_string_number", fields={"VALUE": [name, None]})


def sum_tree(terms):
    """Balanced add tree."""
    terms = list(terms)
    while len(terms) > 1:
        nxt = []
        for i in range(0, len(terms) - 1, 2):
            nxt.append(add(terms[i], terms[i + 1]))
        if len(terms) % 2:
            nxt.append(terms[-1])
        terms = nxt
    return terms[0]


class Prog:
    """Program-building context bound to a Project + target."""

    def __init__(self, P, target):
        self.P = P
        self.t = target

    # data
    def v(self, name): return self.P.V(name)
    def item(self, l, i): return Blk("data_itemoflist", {"INDEX": (i, INT)}, {"LIST": self.P.L(l)})
    def itemnum(self, l, x): return Blk("data_itemnumoflist", {"ITEM": (x, TEXT)}, {"LIST": self.P.L(l)})
    def llen(self, l): return Blk("data_lengthoflist", {}, {"LIST": self.P.L(l)})

    def set(self, name, e): return Blk("data_setvariableto", {"VALUE": (e, TEXT)}, {"VARIABLE": [name, self.P.vars[name][0]]})
    def change(self, name, e): return Blk("data_changevariableby", {"VALUE": (e, NUM)}, {"VARIABLE": [name, self.P.vars[name][0]]})
    def addto(self, l, e): return Blk("data_addtolist", {"ITEM": (e, TEXT)}, {"LIST": self.P.L(l)})
    def replace(self, l, i, e): return Blk("data_replaceitemoflist", {"INDEX": (i, INT), "ITEM": (e, TEXT)}, {"LIST": self.P.L(l)})
    def delitem(self, l, i): return Blk("data_deleteoflist", {"INDEX": (i, INT)}, {"LIST": self.P.L(l)})
    def delall(self, l): return Blk("data_deletealloflist", {}, {"LIST": self.P.L(l)})

    # control
    def repeat(self, n, body): return Blk("control_repeat", {"TIMES": (n, WHOLE), "SUBSTACK": (body, None)})
    def until(self, cond, body): return Blk("control_repeat_until", {"CONDITION": (cond, None), "SUBSTACK": (body, None)})
    def forever(self, body): return Blk("control_forever", {"SUBSTACK": (body, None)})

    def if_(self, cond, body, else_=None):
        if else_ is None:
            return Blk("control_if", {"CONDITION": (cond, None), "SUBSTACK": (body, None)})
        return Blk("control_if_else", {"CONDITION": (cond, None), "SUBSTACK": (body, None), "SUBSTACK2": (else_, None)})

    def wait(self, s): return Blk("control_wait", {"DURATION": (s, POS)})

    def stop_script(self):
        return Blk("control_stop", {}, {"STOP_OPTION": ["this script", None]},
                   mutation={"tagName": "mutation", "children": [], "hasnext": "false"})

    def say(self, e): return Blk("looks_say", {"MESSAGE": (e, TEXT)})
    def ask(self, e): return Blk("sensing_askandwait", {"QUESTION": (e, TEXT)})
    def broadcast_wait(self, name): return Blk("event_broadcastandwait", {"BROADCAST_INPUT": (Lit(name), BCAST)})

    def call(self, name, *args):
        pr = self.P.procs[name]
        assert len(args) == len(pr["argids"]), name
        inputs = {aid: (a, TEXT) for aid, a in zip(pr["argids"], args)}
        return Blk("procedures_call", inputs, mutation={
            "tagName": "mutation", "children": [], "proccode": pr["proccode"],
            "argumentids": json.dumps(pr["argids"]), "warp": "true" if pr["warp"] else "false"})

    def flag_hat(self): return Blk("event_whenflagclicked")

    def recv_hat(self, name):
        return Blk("event_whenbroadcastreceived", {}, {"BROADCAST_OPTION": [name, self.P.broadcasts[name]]})


def validate(project_json):
    """Structural checks; raises AssertionError on the first problem."""
    targets = project_json["targets"]
    stage = targets[0]
    assert stage["isStage"]
    gvars = set(stage["variables"])
    glists = set(stage["lists"])
    gb = set(stage["broadcasts"])
    all_ids = set()
    protos = {}
    calls = []
    for t in targets:
        B = t["blocks"]
        lvars = gvars | set(t["variables"])
        llists = glists | set(t["lists"])
        for bid in B:
            assert bid not in all_ids, "duplicate id " + bid
            all_ids.add(bid)
        for bid, b in B.items():
            if b["topLevel"]:
                assert b["parent"] is None and "x" in b and "y" in b, bid
            else:
                assert b["parent"] in B, (bid, b["parent"])
            if b["next"] is not None:
                assert b["next"] in B and B[b["next"]]["parent"] == bid, ("next/parent", bid)
            for k, inp in b["inputs"].items():
                assert isinstance(inp, list) and inp[0] in (1, 2, 3), (bid, k, inp)
                if inp[0] == 1:
                    payload = inp[1]
                    if isinstance(payload, str):  # only allowed: prototype arg shadows / custom_block
                        assert payload in B and B[payload]["shadow"], ("[1, id] to non-shadow", bid, k)
                        assert b["opcode"] in ("procedures_definition", "procedures_prototype"), ("[1, blockId]", bid, k)
                    else:
                        assert isinstance(payload, list) and payload[0] in (4, 5, 6, 7, 8, 10, 11), (bid, k, inp)
                elif inp[0] == 2:
                    assert inp[1] in B and B[inp[1]]["parent"] == bid, ("[2] link", bid, k)
                else:
                    assert len(inp) == 3 and inp[1] in B and B[inp[1]]["parent"] == bid, ("[3] link", bid, k)
                    assert isinstance(inp[2], list) and inp[2][0] in (4, 5, 6, 7, 10), ("[3] shadow", bid, k)
            for k, f in b["fields"].items():
                if k == "VARIABLE":
                    assert f[1] in lvars, ("undeclared variable", f)
                if k == "LIST":
                    assert f[1] in llists, ("undeclared list", f)
                if k == "BROADCAST_OPTION":
                    assert f[1] in gb, ("undeclared broadcast", f)
            if b["opcode"] == "procedures_prototype":
                m = b["mutation"]
                ids = json.loads(m["argumentids"])
                assert len(ids) == len(json.loads(m["argumentnames"])) == len(json.loads(m["argumentdefaults"]))
                assert set(ids) == set(b["inputs"]), ("proto inputs", bid)
                protos[m["proccode"]] = ids
            if b["opcode"] == "procedures_call":
                calls.append((bid, b))
    for bid, b in calls:
        m = b["mutation"]
        assert m["proccode"] in protos, ("call to undefined proc", m["proccode"])
        assert json.loads(m["argumentids"]) == protos[m["proccode"]], ("argumentids mismatch", bid)
        assert set(b["inputs"]) <= set(protos[m["proccode"]]), ("call inputs", bid)
    return len(all_ids)


def grep_bad_inputs(text, block_ids):
    """Fail on any [1, "<blockId>"] / [1,[..]] whose payload is a block id outside procedure plumbing."""
    import re
    bad = []
    for m in re.finditer(r'\[1,\s*"([^"]+)"\]', text):
        bad.append(m.group(1))
    # every such occurrence must be a procedures_definition/prototype shadow reference
    return bad
