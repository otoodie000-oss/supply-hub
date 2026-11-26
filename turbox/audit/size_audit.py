"""Size audit of a .sb3: bytes per list / variable group / blocks / assets, raw and deflated
(each part compressed on its own with zlib level 9, which approximates its share of the zip)."""
import json
import re
import sys
import zipfile
import zlib
from collections import defaultdict


def group_of(name):
    # collapse numbered chunks: L3_qkv_q_2 -> L*_qkv_q, fact_tok_5 -> fact_tok
    g = re.sub(r"\d+", "#", name)
    return g


def main(path, out):
    z = zipfile.ZipFile(path)
    info = {i.filename: (i.file_size, i.compress_size) for i in z.infolist()}
    pj = json.loads(z.read("project.json"))
    res = {"sb3_bytes": sum(c for _, c in info.values()), "files": info}
    groups = defaultdict(lambda: [0, 0, 0, 0])  # raw, deflated, items, lists
    blocks = {}
    for t in pj["targets"]:
        blocks[t["name"]] = len(t["blocks"])
        for lid, (name, vals) in t["lists"].items():
            raw = json.dumps(vals).encode()
            g = groups[group_of(name)]
            g[0] += len(raw)
            g[1] += len(zlib.compress(raw, 9))
            g[2] += len(vals)
            g[3] += 1
    braw = json.dumps([t["blocks"] for t in pj["targets"]]).encode()
    res["blocks_per_target"] = blocks
    res["blocks_json"] = [len(braw), len(zlib.compress(braw, 9))]
    rows = sorted(groups.items(), key=lambda kv: -kv[1][1])
    res["list_groups"] = [{"group": k, "raw": v[0], "deflated": v[1], "items": v[2], "lists": v[3]} for k, v in rows]
    tot = sum(v[1] for v in groups.values())
    res["lists_deflated_total"] = tot
    json.dump(res, open(out, "w"), indent=1)
    print("sb3", res["sb3_bytes"], "blocks", blocks, "blocks_json raw/defl", res["blocks_json"])
    print("lists deflated total", tot)
    for r in res["list_groups"][:25]:
        print("%-22s raw %10d defl %9d items %8d lists %d" % (r["group"], r["raw"], r["deflated"], r["items"], r["lists"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
