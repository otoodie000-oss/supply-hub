"""Build a small .sb3 containing only the helper blocks + a batch test runner."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scratch"))
sys.path.insert(0, HERE)
from sscompile import Project, Compiler, validate  # noqa: E402
from sb3 import write_sb3  # noqa: E402
from scratch_tools import tools_source, declare_tool_tables  # noqa: E402

STUB = '''
cfg_now = ""
seed = 12345
timer_end = 0
timer_on = 0
timer_label = ""
tin = List()
tnow = List()
tseed = List()
tout = List()

@proc
def lcg():
    global seed
    seed = (seed * 1664525 + 1013904223) % 4294967296
    return seed / 4294967296
'''
RUNNER = '''
@when_broadcast("tooltest")
def tooltest():
    global cfg_now, seed
    tout.clear()
    for i in range(1, len(tin) + 1):
        cfg_now = tnow[i]
        seed = tseed[i]
        run_tool(tin[i])
        tout.append(run_tool.ret)
'''


def main(cases_path, out):
    cases = json.load(open(cases_path))
    P = Project()
    declare_tool_tables(P)
    C = Compiler(P)
    C.compile_module(STUB, "stub")
    C.compile_module(tools_source(), "tools")
    C.compile_module(RUNNER, "runner")
    P.lst("tin", [c["call"] for c in cases])
    P.lst("tnow", [c["cfg_now"] for c in cases])
    P.lst("tseed", [c["seed"] for c in cases])
    pj, n = write_sb3(P, out)
    print(json.dumps(validate(pj)), n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
