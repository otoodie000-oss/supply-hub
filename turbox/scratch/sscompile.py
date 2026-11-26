"""ScratchScript: compile a small Python subset into Scratch 3 blocks (project.json).

Why: Turbo 2.0 needs thousands of blocks (transformer kernels, tokenizer, BM25, ~30
helpers, sampling, UI).  Writing them as Python-syntax source keeps them reviewable and
lets the Python side run the same algorithms for testing.

Language (parsed with `ast`):
  module level   NAME = 0 / "txt"            -> global Stage variable with initial value
                 NAME = List() / List([...]) -> global Stage list (items embedded)
                 @proc / @proc(warp=False)    -> custom block ("run without screen refresh"
                                                 unless warp=False); args are string/number
                 @when_flag / @when_broadcast("msg") / @when_flag_stage ... -> hat scripts
  statements     x = e | x += e | x -= e | if/elif/else | while c: | for i in range(a, b):
                 L.append(v) L.clear() L.insert(i, v) L.delete(i) L[i] = v  (1-based!)
                 return [e] | pass | global x | proc_call(args) | builtin statements below
  expressions    numbers, strings, + - * / % //  (+ is NUMERIC; use join() for text)
                 < > == != <= >= and or not, L[i] (item i of L, 1-based), len(L),
                 v in L (list contains), user proc calls (value via return)
  builtins       join(a,b) letter(i,s) strlen(s) contains(s,t) floor ceil abs sqrt ln exp
                 round  index_of(L,v)  rand(a,b)  current("year"|...)  days2000()  timer()
                 answer()  bool_str(c)
  stmt builtins  say(x) say_secs(x,s) ask(q) wait(s) wait_until(c) broadcast(m)
                 broadcast_wait(m) stop_all() reset_timer()
Locals are globals prefixed with "<proc>." (Scratch has no locals; no recursion allowed).
Return values live in "<proc>.ret".

Serialization rules enforced here (they broke earlier builds):
  * reporter in an input slot  -> [3, blockId, [shadowType, value]]  (never [1, blockId])
  * literal                    -> [1, [4|10, "v"]]  (broadcast menus use [1,[11,name,id]])
  * boolean / substack         -> [2, blockId]
  * variables are full data_variable blocks; parent/next consistent; unique ids;
    top-level blocks have x/y; prototype/call proccode + argumentids match;
    all variables/lists/broadcasts declared on the Stage.
  The only [1, blockId] inputs are the two canonical shadow links Scratch itself uses:
  procedures_definition.custom_block -> prototype, and prototype arg -> argument shadow.
"""
import ast
import json
import re

NUM, TEXT, BCAST = 4, 10, 11


class CompileError(Exception):
    pass


class List:  # marker for module-level list declarations
    def __init__(self, items=None):
        self.items = items or []


def fmt_lit(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return repr(v)
    return str(v)


class Project:
    def __init__(self):
        self.vars = {}        # name -> [id, value]
        self.lists = {}       # name -> [id, items]
        self.broadcasts = {}  # name -> id
        self.procs = {}       # name -> {proccode, argids, argnames, warp}
        self.sprite_blocks = {}   # sprite name -> blocks (in project.json order)
        self.sprite_y = {}
        self.stage_blocks = {}
        self._n = 0
        self._y = 0
        self._ys = 0

    # ---------------------------------------------------------- declarations
    def var(self, name, value=0):
        if name not in self.vars:
            self.vars[name] = ["v%d_%s" % (len(self.vars), re.sub(r"[^A-Za-z0-9_]", "_", name)), value]
        return name

    def lst(self, name, items=None):
        if name not in self.lists:
            self.lists[name] = ["l%d_%s" % (len(self.lists), re.sub(r"[^A-Za-z0-9_]", "_", name)), list(items or [])]
        elif items is not None:
            self.lists[name][1] = list(items)
        return name

    def bcast(self, name):
        if name not in self.broadcasts:
            self.broadcasts[name] = "b%d_%s" % (len(self.broadcasts), re.sub(r"[^A-Za-z0-9_]", "_", name))
        return name

    def nid(self):
        self._n += 1
        return "k%d" % self._n

    def to_targets_multi(self, sprites, costume_stage):
        """sprites: list of dicts {name, costumes, visible, x, y, size}; order = project.json order
        (the first sprite is the one the editor opens on)."""
        stage = {
            "isStage": True, "name": "Stage",
            "variables": {vid: [n, v] for n, (vid, v) in self.vars.items()},
            "lists": {lid: [n, items] for n, (lid, items) in self.lists.items()},
            "broadcasts": {bid: n for n, bid in self.broadcasts.items()},
            "blocks": self.stage_blocks, "comments": {}, "currentCostume": 0,
            "costumes": [costume_stage], "sounds": [], "volume": 100, "layerOrder": 0,
            "tempo": 60, "videoTransparency": 50, "videoState": "on", "textToSpeechLanguage": None,
        }
        out = [stage]
        for k, sp in enumerate(sprites):
            out.append({
                "isStage": False, "name": sp["name"], "variables": {}, "lists": {}, "broadcasts": {},
                "blocks": self.sprite_blocks.get(sp["name"], {}), "comments": {}, "currentCostume": 0,
                "costumes": sp["costumes"], "sounds": [], "volume": 100, "layerOrder": k + 1,
                "visible": sp.get("visible", True), "x": sp.get("x", 0), "y": sp.get("y", 0),
                "size": sp.get("size", 100), "direction": 90, "draggable": False, "rotationStyle": "all around"})
        return out

    def to_targets(self, costumes_sprite, costume_stage, sprite_name="Turbo"):
        stage = {
            "isStage": True, "name": "Stage",
            "variables": {vid: [n, v] for n, (vid, v) in self.vars.items()},
            "lists": {lid: [n, items] for n, (lid, items) in self.lists.items()},
            "broadcasts": {bid: n for n, bid in self.broadcasts.items()},
            "blocks": self.stage_blocks, "comments": {}, "currentCostume": 0,
            "costumes": [costume_stage], "sounds": [], "volume": 100, "layerOrder": 0,
            "tempo": 60, "videoTransparency": 50, "videoState": "on", "textToSpeechLanguage": None,
        }
        sprite = {
            "isStage": False, "name": sprite_name, "variables": {}, "lists": {}, "broadcasts": {},
            "blocks": self.sprite_blocks.get(sprite_name, {}), "comments": {}, "currentCostume": 0, "costumes": costumes_sprite,
            "sounds": [], "volume": 100, "layerOrder": 1, "visible": True, "x": -150, "y": -60, "size": 100,
            "direction": 90, "draggable": False, "rotationStyle": "all around",
        }
        return [stage, sprite]


class Compiler:
    """Compiles one ScratchScript module (source text) into Project blocks."""

    def __init__(self, project: Project):
        self.P = project
        self.B = None          # current blocks dict
        self.fn = None         # current proc name or None
        self.args = set()
        self.globals_decl = set()
        self.tmp = 0
        self.module_names = set()
        self.cur_sprite = "Turbo"

    # ---------------------------------------------------------- module
    def compile_module(self, src, filename="<ss>"):
        self.compile_all([(src, filename)])

    def compile_all(self, modules):
        """Declare every module first (cross-module procs/variables), then emit bodies.
        modules: (src, filename) or (src, filename, sprite_name); default sprite "Turbo".
        Custom blocks belong to one sprite: calling a proc of another sprite is a compile error."""
        mods = [(m[0], m[1], m[2] if len(m) > 2 else "Turbo") for m in modules]
        trees = []
        for src, fn, sp in mods:
            self.cur_sprite = sp
            self.P.sprite_blocks.setdefault(sp, {})
            trees.append((self._declare_module(src, fn), sp))
        for tree, sp in trees:
            self.cur_sprite = sp
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    self._compile_function(node, self._deco(node))

    def _declare_module(self, src, filename):
        tree = ast.parse(src, filename)
        # pass 1: declarations and proc signatures
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                v = node.value
                if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "List":
                    items = ast.literal_eval(v.args[0]) if v.args else []
                    self.P.lst(name, items)
                else:
                    self.P.var(name, ast.literal_eval(v))
                self.module_names.add(name)
            elif isinstance(node, ast.FunctionDef):
                deco = self._deco(node)
                if deco[0] == "proc":
                    self._declare_proc(node, deco[1])
            elif isinstance(node, (ast.Expr,)) and isinstance(node.value, ast.Constant):
                pass  # docstring
            else:
                raise CompileError("%s:%d unsupported module statement" % (filename, node.lineno))
        return tree

    def _deco(self, node):
        if not node.decorator_list:
            return ("proc", {"warp": True})
        d = node.decorator_list[0]
        if isinstance(d, ast.Name):
            return (d.id, {"warp": True} if d.id == "proc" else {})
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            kw = {k.arg: ast.literal_eval(k.value) for k in d.keywords}
            args = [ast.literal_eval(a) for a in d.args]
            if d.func.id == "proc":
                return ("proc", {"warp": kw.get("warp", True)})
            return (d.func.id, {"args": args, **kw})
        raise CompileError("bad decorator")

    def _declare_proc(self, node, opts):
        name = node.name
        argnames = [a.arg for a in node.args.args]
        if name in self.P.procs:
            raise CompileError("duplicate proc " + name)
        argids = ["a_%s_%s" % (name, a) for a in argnames]
        proccode = name + "".join(" %s" for _ in argnames)
        self.P.procs[name] = {"proccode": proccode, "argids": argids, "argnames": argnames,
                              "warp": bool(opts.get("warp", True)), "sprite": self.cur_sprite}
        self.P.var(name + ".ret", 0)

    # ---------------------------------------------------------- block helpers
    def blk(self, opcode, parent, inputs=None, fields=None, shadow=False, mutation=None, top=False):
        bid = self.P.nid()
        d = {"opcode": opcode, "next": None, "parent": parent, "inputs": inputs or {}, "fields": fields or {},
             "shadow": shadow, "topLevel": top}
        if mutation is not None:
            d["mutation"] = mutation
        self.B[bid] = d
        return bid

    def set_parent(self, bid, parent):
        self.B[bid]["parent"] = parent

    # ---------------------------------------------------------- functions / hats
    def _compile_function(self, node, deco):
        kind, opts = deco
        self.fn = node.name if kind == "proc" else "_" + node.name
        self.args = set(a.arg for a in node.args.args) if kind == "proc" else set()
        self.globals_decl = set()
        for st in ast.walk(node):
            if isinstance(st, ast.Global):
                self.globals_decl.update(st.names)
        stage = kind.endswith("_stage")
        self.B = self.P.stage_blocks if stage else self.P.sprite_blocks[self.cur_sprite]
        if stage:
            kind = kind[:-6]
            y = self.P._ys
            self.P._ys += 400
        else:
            y = self.P.sprite_y.get(self.cur_sprite, 0)
            self.P.sprite_y[self.cur_sprite] = y + 400
        if kind == "proc":
            info = self.P.procs[node.name]
            hat = self.blk("procedures_definition", None, top=True)
            self.B[hat]["x"], self.B[hat]["y"] = 0, y
            proto = self.blk("procedures_prototype", hat, shadow=True)
            pinputs = {}
            for aid, an in zip(info["argids"], info["argnames"]):
                sh = self.blk("argument_reporter_string_number", proto, fields={"VALUE": [an, None]}, shadow=True)
                pinputs[aid] = [2, sh]
            self.B[proto]["inputs"] = pinputs
            self.B[proto]["mutation"] = {"tagName": "mutation", "children": [], "proccode": info["proccode"],
                                         "argumentids": json.dumps(info["argids"]),
                                         "argumentnames": json.dumps(info["argnames"]),
                                         "argumentdefaults": json.dumps(["" for _ in info["argids"]]),
                                         "warp": "true" if info["warp"] else "false"}
            self.B[hat]["inputs"] = {"custom_block": [2, proto]}
        elif kind == "when_flag":
            hat = self.blk("event_whenflagclicked", None, top=True)
            self.B[hat]["x"], self.B[hat]["y"] = 0, y
        elif kind == "when_broadcast":
            msg = opts["args"][0]
            self.P.bcast(msg)
            hat = self.blk("event_whenbroadcastreceived", None, top=True,
                           fields={"BROADCAST_OPTION": [msg, self.P.broadcasts[msg]]})
            self.B[hat]["x"], self.B[hat]["y"] = 0, y
        else:
            raise CompileError("unknown hat " + kind)
        first = self.stmts(node.body, hat)
        if first:
            self.B[hat]["next"] = first
            self.set_parent(first, hat)
        self.fn = None

    # ---------------------------------------------------------- statements
    def stmts(self, body, parent):
        """Compile a statement list; returns first block id (chained via next)."""
        ids = []
        for st in body:
            ids.extend(self.stmt(st))
        if not ids:
            return None
        for a, b in zip(ids, ids[1:]):
            self.B[a]["next"] = b
            self.B[b]["parent"] = a
        self.B[ids[0]]["parent"] = parent
        return ids[0]

    def substack(self, body, parent):
        first = self.stmts(body, parent)
        return [2, first] if first else None

    def varname(self, name):
        if name in self.args:
            raise CompileError("cannot assign to argument %s in %s" % (name, self.fn))
        if name in self.globals_decl:
            return self.P.var(name)
        if name in self.module_names:
            raise CompileError("%s assigns module name %s without 'global'" % (self.fn, name))
        return self.P.var(self.fn + "." + name)

    def read_varname(self, name):
        if name in self.globals_decl:
            return name
        local = (self.fn or "") + "." + name
        if local in self.P.vars:
            return local
        if name in self.module_names or name in self.P.vars:
            return name
        raise CompileError("unknown variable %s in %s" % (name, self.fn))

    def setvar(self, vname, expr_node, parent=None):
        pre, val = self.expr_hoisted(expr_node)
        bid = self.blk("data_setvariableto", parent, fields={"VARIABLE": [vname, self.P.vars[vname][0]]})
        self.B[bid]["inputs"]["VALUE"] = self.slot(val, bid, TEXT)
        return pre + [bid]

    def stmt(self, st):
        if isinstance(st, ast.Assign):
            if len(st.targets) != 1:
                raise CompileError("multiple assignment")
            t = st.targets[0]
            if isinstance(t, ast.Name):
                return self.setvar(self.varname(t.id), st.value)
            if isinstance(t, ast.Subscript):
                lname = self._listname(t.value)
                pre1, idx = self.expr_hoisted(t.slice)
                pre2, val = self.expr_hoisted(st.value)
                bid = self.blk("data_replaceitemoflist", None, fields={"LIST": [lname, self.P.lists[lname][0]]})
                self.B[bid]["inputs"]["INDEX"] = self.slot(idx, bid, NUM)
                self.B[bid]["inputs"]["ITEM"] = self.slot(val, bid, TEXT)
                return pre1 + pre2 + [bid]
            raise CompileError("bad assign target")
        if isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name):
            vname = self.varname(st.target.id)
            if isinstance(st.op, (ast.Add, ast.Sub)):
                node = st.value if isinstance(st.op, ast.Add) else ast.UnaryOp(op=ast.USub(), operand=st.value)
                pre, val = self.expr_hoisted(node)
                bid = self.blk("data_changevariableby", None, fields={"VARIABLE": [vname, self.P.vars[vname][0]]})
                self.B[bid]["inputs"]["VALUE"] = self.slot(val, bid, NUM)
                return pre + [bid]
            return self.setvar(vname, ast.BinOp(left=ast.Name(id=st.target.id, ctx=ast.Load()), op=st.op, right=st.value))
        if isinstance(st, ast.If):
            pre, cond = self.expr_hoisted(st.test, boolean=True)
            if st.orelse:
                bid = self.blk("control_if_else", None)
                ins = {"CONDITION": self.bslot(cond, bid)}
                s1 = self.substack(st.body, bid)
                s2 = self.substack(st.orelse, bid)
                if s1:
                    ins["SUBSTACK"] = s1
                if s2:
                    ins["SUBSTACK2"] = s2
            else:
                bid = self.blk("control_if", None)
                ins = {"CONDITION": self.bslot(cond, bid)}
                s1 = self.substack(st.body, bid)
                if s1:
                    ins["SUBSTACK"] = s1
            if ins["CONDITION"] is None:
                del ins["CONDITION"]
            self.B[bid]["inputs"] = ins
            return pre + [bid]
        if isinstance(st, ast.While):
            if self._has_call(st.test):
                raise CompileError("calls in while conditions are not supported (line %d)" % st.lineno)
            if isinstance(st.test, ast.Constant) and st.test.value is True and self.fn.startswith("_"):
                bid = self.blk("control_forever", None)
                s = self.substack(st.body, bid)
                if s:
                    self.B[bid]["inputs"]["SUBSTACK"] = s
                return [bid]
            bid = self.blk("control_repeat_until", None)
            _, cond = self.expr_hoisted(ast.UnaryOp(op=ast.Not(), operand=st.test), boolean=True)
            ins = {"CONDITION": self.bslot(cond, bid)}
            s = self.substack(st.body, bid)
            if s:
                ins["SUBSTACK"] = s
            self.B[bid]["inputs"] = ins
            return [bid]
        if isinstance(st, ast.For):
            # for i in range(a, b) / range(n) / range(a, b, -1)
            if not (isinstance(st.iter, ast.Call) and isinstance(st.iter.func, ast.Name) and st.iter.func.id == "range"):
                raise CompileError("only for-range loops")
            ra = st.iter.args
            if len(ra) == 1:
                a, b, step = ast.Constant(0), ra[0], 1
            else:
                a, b = ra[0], ra[1]
                step = ast.literal_eval(ra[2]) if len(ra) > 2 else 1
            if step not in (1, -1):
                raise CompileError("range step must be +-1")
            vname = self.varname(st.target.id)
            out = self.setvar(vname, a)
            count = ast.BinOp(left=b, op=ast.Sub(), right=a) if step == 1 else ast.BinOp(left=a, op=ast.Sub(), right=b)
            pre, cnt = self.expr_hoisted(count)
            bid = self.blk("control_repeat", None)
            body_ids = []
            for s2 in st.body:
                body_ids.extend(self.stmt(s2))
            ch = self.blk("data_changevariableby", None, fields={"VARIABLE": [vname, self.P.vars[vname][0]]})
            self.B[ch]["inputs"]["VALUE"] = [1, [NUM, str(step)]]
            body_ids.append(ch)
            for x, y in zip(body_ids, body_ids[1:]):
                self.B[x]["next"] = y
                self.B[y]["parent"] = x
            self.B[body_ids[0]]["parent"] = bid
            self.B[bid]["inputs"] = {"TIMES": self.slot(cnt, bid, NUM), "SUBSTACK": [2, body_ids[0]]}
            return out + pre + [bid]
        if isinstance(st, ast.Return):
            out = []
            if st.value is not None:
                if self.fn.startswith("_"):
                    raise CompileError("return value outside proc")
                out = self.setvar(self.fn + ".ret", st.value)
            bid = self.blk("control_stop", None, fields={"STOP_OPTION": ["this script", None]},
                           mutation={"tagName": "mutation", "children": [], "hasnext": "false"})
            return out + [bid]
        if isinstance(st, ast.Pass) or isinstance(st, ast.Global):
            return []
        if isinstance(st, ast.Expr):
            if isinstance(st.value, ast.Constant):
                return []  # docstring
            if isinstance(st.value, ast.Call):
                return self.call_stmt(st.value)
        raise CompileError("unsupported statement at line %d: %s" % (st.lineno, ast.dump(st)[:80]))

    def _listname(self, node):
        if isinstance(node, ast.Name) and node.id in self.P.lists:
            return node.id
        raise CompileError("unknown list %s" % ast.dump(node)[:60])

    def _has_call(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in self.P.procs:
                return True
        return False

    def call_stmt(self, c):
        f = c.func
        if isinstance(f, ast.Attribute):  # list methods
            lname = self._listname(f.value)
            lf = {"LIST": [lname, self.P.lists[lname][0]]}
            pre, vals = [], []
            for a in c.args:
                p, v = self.expr_hoisted(a)
                pre += p
                vals.append(v)
            m = f.attr
            if m == "append":
                bid = self.blk("data_addtolist", None, fields=lf)
                self.B[bid]["inputs"]["ITEM"] = self.slot(vals[0], bid, TEXT)
            elif m == "clear":
                bid = self.blk("data_deletealloflist", None, fields=lf)
            elif m == "delete":
                bid = self.blk("data_deleteoflist", None, fields=lf)
                self.B[bid]["inputs"]["INDEX"] = self.slot(vals[0], bid, NUM)
            elif m == "insert":
                bid = self.blk("data_insertatlist", None, fields=lf)
                self.B[bid]["inputs"]["INDEX"] = self.slot(vals[0], bid, NUM)
                self.B[bid]["inputs"]["ITEM"] = self.slot(vals[1], bid, TEXT)
            else:
                raise CompileError("list method " + m)
            return pre + [bid]
        name = f.id
        if name in self.P.procs:
            return self.proc_call(name, c.args)
        pre, vals = [], []
        for a in c.args:
            if name in ("wait_until",):
                p, v = self.expr_hoisted(a, boolean=True)
            elif name in ("broadcast", "broadcast_wait"):
                p, v = [], ("lit", ast.literal_eval(a))
            else:
                p, v = self.expr_hoisted(a)
            pre += p
            vals.append(v)
        simple = {"say": ("looks_say", ["MESSAGE"], [TEXT]), "think": ("looks_think", ["MESSAGE"], [TEXT]),
                  "say_secs": ("looks_sayforsecs", ["MESSAGE", "SECS"], [TEXT, NUM]),
                  "ask": ("sensing_askandwait", ["QUESTION"], [TEXT]),
                  "wait": ("control_wait", ["DURATION"], [NUM])}
        if name in simple:
            op, keys, types = simple[name]
            bid = self.blk(op, None)
            for k, v, t in zip(keys, vals, types):
                self.B[bid]["inputs"][k] = self.slot(v, bid, t)
            return pre + [bid]
        if name == "wait_until":
            bid = self.blk("control_wait_until", None)
            self.B[bid]["inputs"]["CONDITION"] = self.bslot(vals[0], bid)
            return pre + [bid]
        if name in ("broadcast", "broadcast_wait"):
            msg = vals[0][1]
            self.P.bcast(msg)
            bid = self.blk("event_broadcast" if name == "broadcast" else "event_broadcastandwait", None)
            self.B[bid]["inputs"]["BROADCAST_INPUT"] = [1, [BCAST, msg, self.P.broadcasts[msg]]]
            return pre + [bid]
        if name == "stop_all":
            return pre + [self.blk("control_stop", None, fields={"STOP_OPTION": ["all", None]},
                                   mutation={"tagName": "mutation", "children": [], "hasnext": "false"})]
        if name == "reset_timer":
            return pre + [self.blk("sensing_resettimer", None)]
        if name == "show_list" or name == "hide_list":
            lname = c.args[0].id
            return [self.blk("data_showlist" if name == "show_list" else "data_hidelist", None,
                             fields={"LIST": [lname, self.P.lists[lname][0]]})]
        if name == "show_var" or name == "hide_var":
            vname = c.args[0].id
            return [self.blk("data_showvariable" if name == "show_var" else "data_hidevariable", None,
                             fields={"VARIABLE": [vname, self.P.vars[vname][0]]})]
        raise CompileError("unknown statement call %s" % name)

    def proc_call(self, name, argnodes):
        info = self.P.procs[name]
        if self.B is not self.P.sprite_blocks.get(info["sprite"]):
            raise CompileError("proc %s belongs to sprite %s; called from another target" % (name, info["sprite"]))
        if len(argnodes) != len(info["argids"]):
            raise CompileError("arity mismatch calling %s" % name)
        pre, vals = [], []
        for a in argnodes:
            p, v = self.expr_hoisted(a)
            pre += p
            vals.append(v)
        bid = self.blk("procedures_call", None,
                       mutation={"tagName": "mutation", "children": [], "proccode": info["proccode"],
                                 "argumentids": json.dumps(info["argids"]), "warp": "true" if info["warp"] else "false"})
        for aid, v in zip(info["argids"], vals):
            self.B[bid]["inputs"][aid] = self.slot(v, bid, TEXT)
        return pre + [bid]

    # ---------------------------------------------------------- expressions
    # an expression value is ("lit", python_value) | ("rep", blockId) | ("bool", blockId)
    def expr_hoisted(self, node, boolean=False):
        """Hoist user-proc calls out of `node` into statements; return (pre_stmts, value)."""
        pre = []
        node = self._hoist(node, pre)
        return pre, self.expr(node, boolean)

    def _hoist(self, node, pre):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in self.P.procs:
            args = [self._hoist(a, pre) for a in node.args]
            pre.extend(self.proc_call(node.func.id, args))
            self.tmp += 1
            tname = (self.fn or "") + ".t%d" % self.tmp
            self.P.var(tname)
            ret = ast.Name(id="__ret__" + node.func.id, ctx=ast.Load())
            bid = self.blk("data_setvariableto", None, fields={"VARIABLE": [tname, self.P.vars[tname][0]]})
            self.B[bid]["inputs"]["VALUE"] = self.slot(self.expr(ret), bid, TEXT)
            pre.append(bid)
            return ast.Name(id="__var__" + tname, ctx=ast.Load())
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                setattr(node, field, self._hoist(value, pre))
            elif isinstance(value, list):
                setattr(node, field, [self._hoist(v, pre) if isinstance(v, ast.AST) else v for v in value])
        return node

    def slot(self, val, parent, shadow_type):
        kind, v = val
        if kind == "lit":
            return [1, [shadow_type if not isinstance(v, str) or shadow_type == TEXT else TEXT, fmt_lit(v)]]
        self.set_parent(v, parent)
        return [3, v, [shadow_type, "" if shadow_type == TEXT else "0"]]

    def bslot(self, val, parent):
        kind, v = val
        if kind == "lit":
            if v is True or v == "true":
                # constant true: not(false-ish empty) -> use operator_not with empty slot
                b = self.blk("operator_not", parent)
                return [2, b]
            return None  # empty boolean slot = false
        self.set_parent(v, parent)
        return [2, v]

    def var_block(self, vname):
        return self.blk("data_variable", None, fields={"VARIABLE": [vname, self.P.vars[vname][0]]})

    def expr(self, node, boolean=False):
        e = self._expr(node)
        if boolean and e[0] == "rep":
            # value used as condition: (v = "true")
            b = self.blk("operator_equals", None)
            self.B[b]["inputs"]["OPERAND1"] = self.slot(e, b, TEXT)
            self.B[b]["inputs"]["OPERAND2"] = [1, [TEXT, "true"]]
            return ("bool", b)
        return e

    def _binop(self, opcode, k1, k2, a, b, t=NUM):
        bid = self.blk(opcode, None)
        ea, eb = self._expr(a), self._expr(b)
        self.B[bid]["inputs"][k1] = self.slot(ea, bid, t) if ea[0] != "bool" else self.slot(ea, bid, t)
        self.B[bid]["inputs"][k2] = self.slot(eb, bid, t)
        return ("rep", bid)

    def _mathop(self, op, a):
        bid = self.blk("operator_mathop", None, fields={"OPERATOR": [op, None]})
        self.B[bid]["inputs"]["NUM"] = self.slot(self._expr(a), bid, NUM)
        return ("rep", bid)

    def _bool(self, opcode, keys, nodes, t=TEXT):
        bid = self.blk(opcode, None)
        for k, n in zip(keys, nodes):
            e = self._expr(n)
            self.B[bid]["inputs"][k] = self.slot(e, bid, t)
        return ("bool", bid)

    def _expr(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return ("lit", node.value)
            return ("lit", node.value)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                if isinstance(node.operand, ast.Constant):
                    return ("lit", -node.operand.value)
                return self._binop("operator_subtract", "NUM1", "NUM2", ast.Constant(0), node.operand)
            if isinstance(node.op, ast.Not):
                bid = self.blk("operator_not", None)
                e = self.expr(node.operand, boolean=True)
                s = self.bslot(e, bid)
                if s:
                    self.B[bid]["inputs"]["OPERAND"] = s
                return ("bool", bid)
            if isinstance(node.op, ast.UAdd):
                return self._expr(node.operand)
        if isinstance(node, ast.Name):
            if node.id.startswith("__ret__"):
                return ("rep", self.var_block(node.id[7:] + ".ret"))
            if node.id.startswith("__var__"):
                return ("rep", self.var_block(node.id[7:]))
            if node.id in self.args:
                return ("rep", self.blk("argument_reporter_string_number", None, fields={"VALUE": [node.id, None]}))
            if node.id in ("True", "False"):
                return ("lit", node.id == "True")
            return ("rep", self.var_block(self.read_varname(node.id)))
        if isinstance(node, ast.BinOp):
            ops = {ast.Add: "operator_add", ast.Sub: "operator_subtract", ast.Mult: "operator_multiply",
                   ast.Div: "operator_divide", ast.Mod: "operator_mod"}
            if type(node.op) in ops:
                return self._binop(ops[type(node.op)], "NUM1", "NUM2", node.left, node.right)
            if isinstance(node.op, ast.FloorDiv):
                inner = ast.BinOp(left=node.left, op=ast.Div(), right=node.right)
                return self._mathop("floor", inner)
            raise CompileError("unsupported binop %s" % type(node.op).__name__)
        if isinstance(node, ast.BoolOp):
            opcode = "operator_and" if isinstance(node.op, ast.And) else "operator_or"
            vals = node.values
            acc = self.expr(vals[0], boolean=True)
            for v in vals[1:]:
                bid = self.blk(opcode, None)
                rhs = self.expr(v, boolean=True)
                ins = {}
                s1 = self.bslot(acc, bid)
                s2 = self.bslot(rhs, bid)
                if s1:
                    ins["OPERAND1"] = s1
                if s2:
                    ins["OPERAND2"] = s2
                self.B[bid]["inputs"] = ins
                acc = ("bool", bid)
            return acc
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1:
                raise CompileError("chained comparison")
            op, a, b = node.ops[0], node.left, node.comparators[0]
            if isinstance(op, ast.Lt):
                return self._bool("operator_lt", ["OPERAND1", "OPERAND2"], [a, b])
            if isinstance(op, ast.Gt):
                return self._bool("operator_gt", ["OPERAND1", "OPERAND2"], [a, b])
            if isinstance(op, ast.Eq):
                return self._bool("operator_equals", ["OPERAND1", "OPERAND2"], [a, b])
            if isinstance(op, (ast.LtE, ast.GtE, ast.NotEq)):
                inner = {ast.LtE: ast.Gt, ast.GtE: ast.Lt, ast.NotEq: ast.Eq}[type(op)]
                return self._expr(ast.UnaryOp(op=ast.Not(), operand=ast.Compare(left=a, ops=[inner()], comparators=[b])))
            if isinstance(op, ast.In):
                lname = self._listname(b)
                bid = self.blk("data_listcontainsitem", None, fields={"LIST": [lname, self.P.lists[lname][0]]})
                self.B[bid]["inputs"]["ITEM"] = self.slot(self._expr(a), bid, TEXT)
                return ("bool", bid)
            raise CompileError("unsupported compare")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.attr == "ret" \
                and node.value.id in self.P.procs:
            return ("rep", self.var_block(node.value.id + ".ret"))
        if isinstance(node, ast.Subscript):
            lname = self._listname(node.value)
            bid = self.blk("data_itemoflist", None, fields={"LIST": [lname, self.P.lists[lname][0]]})
            self.B[bid]["inputs"]["INDEX"] = self.slot(self._expr(node.slice), bid, NUM)
            return ("rep", bid)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return self._builtin(node.func.id, node.args)
        raise CompileError("unsupported expression %s" % ast.dump(node)[:100])

    def _builtin(self, name, args):
        if name == "join":
            return self._binop("operator_join", "STRING1", "STRING2", args[0], args[1], TEXT)
        if name == "letter":
            bid = self.blk("operator_letter_of", None)
            self.B[bid]["inputs"]["LETTER"] = self.slot(self._expr(args[0]), bid, NUM)
            self.B[bid]["inputs"]["STRING"] = self.slot(self._expr(args[1]), bid, TEXT)
            return ("rep", bid)
        if name == "strlen":
            bid = self.blk("operator_length", None)
            self.B[bid]["inputs"]["STRING"] = self.slot(self._expr(args[0]), bid, TEXT)
            return ("rep", bid)
        if name == "contains":
            return self._bool("operator_contains", ["STRING1", "STRING2"], args)
        if name in ("floor", "ceil", "abs", "sqrt", "ln", "exp", "log10", "pow10", "sin", "cos", "tan"):
            op = {"ceil": "ceiling", "exp": "e ^", "log10": "log", "pow10": "10 ^"}.get(name, name)
            return self._mathop(op, args[0])
        if name == "round":
            bid = self.blk("operator_round", None)
            self.B[bid]["inputs"]["NUM"] = self.slot(self._expr(args[0]), bid, NUM)
            return ("rep", bid)
        if name == "len":
            lname = self._listname(args[0])
            return ("rep", self.blk("data_lengthoflist", None, fields={"LIST": [lname, self.P.lists[lname][0]]}))
        if name == "index_of":
            lname = self._listname(args[0])
            bid = self.blk("data_itemnumoflist", None, fields={"LIST": [lname, self.P.lists[lname][0]]})
            self.B[bid]["inputs"]["ITEM"] = self.slot(self._expr(args[1]), bid, TEXT)
            return ("rep", bid)
        if name == "rand":
            bid = self.blk("operator_random", None)
            self.B[bid]["inputs"]["FROM"] = self.slot(self._expr(args[0]), bid, NUM)
            self.B[bid]["inputs"]["TO"] = self.slot(self._expr(args[1]), bid, NUM)
            return ("rep", bid)
        if name == "current":
            what = ast.literal_eval(args[0]).upper()
            return ("rep", self.blk("sensing_current", None, fields={"CURRENTMENU": [what, None]}))
        if name == "days2000":
            return ("rep", self.blk("sensing_dayssince2000", None))
        if name == "timer":
            return ("rep", self.blk("sensing_timer", None))
        if name == "answer":
            return ("rep", self.blk("sensing_answer", None))
        if name == "bool_str":  # boolean -> "true"/"false" text via join
            bid = self.blk("operator_join", None)
            e = self.expr(args[0], boolean=True)
            self.set_parent(e[1], bid)
            self.B[bid]["inputs"]["STRING1"] = [3, e[1], [TEXT, ""]]
            self.B[bid]["inputs"]["STRING2"] = [1, [TEXT, ""]]
            return ("rep", bid)
        raise CompileError("unknown function %s" % name)


# ---------------------------------------------------------------- validation
BLOCKID_RE = None


def validate(project_json):
    """Structural checks + serialization grep.  Raises on any problem."""
    stage = project_json["targets"][0]
    var_ids = {k for k in stage["variables"]}
    list_ids = {k for k in stage["lists"]}
    bc_ids = {k for k in stage["broadcasts"]}
    all_ids = set()
    protos = {}
    calls = []
    problems = []
    for t in project_json["targets"]:
        B = t["blocks"]
        for bid, b in B.items():
            if bid in all_ids:
                problems.append("duplicate id " + bid)
            all_ids.add(bid)
        for bid, b in B.items():
            if b["topLevel"]:
                if "x" not in b or "y" not in b:
                    problems.append("top-level without x/y " + bid)
                if b["parent"] is not None:
                    problems.append("top-level with parent " + bid)
            else:
                p = b["parent"]
                if p is None or p not in B:
                    problems.append("dangling parent %s (%s)" % (bid, b["opcode"]))
            if b["next"] is not None:
                n = b["next"]
                if n not in B or B[n]["parent"] != bid:
                    problems.append("bad next link %s -> %s" % (bid, n))
            for k, inp in b["inputs"].items():
                if not isinstance(inp, list):
                    problems.append("input not a list %s.%s" % (bid, k))
                    continue
                if inp[0] == 1:
                    payload = inp[1]
                    if isinstance(payload, str):
                        problems.append("[1, blockId] in %s.%s" % (b["opcode"], k))
                    elif isinstance(payload, list):
                        if payload[0] not in (NUM, TEXT, BCAST):
                            problems.append("literal type %s in %s.%s" % (payload[0], b["opcode"], k))
                        if payload[0] in (NUM, TEXT) and isinstance(payload[1], str) and payload[1] in B:
                            problems.append("literal equals a block id in %s.%s" % (b["opcode"], k))
                        if payload[0] == BCAST and payload[2] not in bc_ids:
                            problems.append("undeclared broadcast " + str(payload))
                elif inp[0] == 2:
                    if not isinstance(inp[1], str) or inp[1] not in B or B[inp[1]]["parent"] != bid:
                        problems.append("bad [2,...] link %s.%s" % (bid, k))
                elif inp[0] == 3:
                    if not isinstance(inp[1], str) or inp[1] not in B or B[inp[1]]["parent"] != bid:
                        problems.append("bad [3,...] reporter %s.%s" % (bid, k))
                    if not (isinstance(inp[2], list) and inp[2][0] in (NUM, TEXT)):
                        problems.append("bad [3,...] shadow %s.%s" % (bid, k))
                else:
                    problems.append("bad input kind %s.%s" % (bid, k))
            for fk in ("VARIABLE",):
                if fk in b["fields"] and b["fields"][fk][1] not in var_ids:
                    problems.append("undeclared variable %s" % b["fields"][fk])
            if "LIST" in b["fields"] and b["fields"]["LIST"][1] not in list_ids:
                problems.append("undeclared list %s" % b["fields"]["LIST"])
            if b["opcode"] == "procedures_prototype":
                m = b["mutation"]
                protos[m["proccode"]] = m["argumentids"]
                ids = json.loads(m["argumentids"])
                if sorted(ids) != sorted(b["inputs"].keys()):
                    problems.append("prototype inputs != argumentids " + m["proccode"])
            if b["opcode"] == "procedures_call":
                calls.append((bid, b["mutation"]["proccode"], b["mutation"]["argumentids"], set(b["inputs"].keys())))
    for bid, pc, aids, keys in calls:
        if pc not in protos:
            problems.append("call to undefined proc " + pc)
        elif protos[pc] != aids:
            problems.append("argumentids mismatch " + pc)
        elif set(json.loads(aids)) != keys:
            problems.append("call inputs != argumentids " + pc)
    # serialization grep over the raw JSON text
    txt = json.dumps({"t": [t["blocks"] for t in project_json["targets"]]})
    for m in re.finditer(r'\[1, "(k\d+)"\]', txt):
        bid = m.group(1)
        # allowed only for the canonical shadow links (already checked structurally above)
        pass
    bad_lit = re.findall(r'\[1, \[(?:4|10), "(k\d+)"\]\]', txt)
    bad_lit = [b for b in bad_lit if b in all_ids]
    if bad_lit:
        problems.append("literal payload equals block id: %s" % bad_lit[:5])
    n_found = len(re.findall(r'\[1,\s*"[^"]*"\]', txt))
    if n_found:
        problems.append("%d inputs of the form [1, <string>] (a [1, ...] payload must be a literal array)" % n_found)
    if problems:
        raise CompileError("validation failed:\n  " + "\n  ".join(problems[:40]))
    return {"blocks": len(all_ids), "procs": len(protos), "one_blockid_links": n_found}
