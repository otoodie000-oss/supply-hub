"""Write a project.json + costumes into a .sb3 zip."""
import hashlib
import io
import json
import zipfile

SPRITE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
<rect x="8" y="14" width="80" height="62" rx="18" fill="#4c97ff" stroke="#3373cc" stroke-width="4"/>
<circle cx="34" cy="42" r="9" fill="#fff"/><circle cx="62" cy="42" r="9" fill="#fff"/>
<circle cx="36" cy="43" r="4" fill="#222"/><circle cx="64" cy="43" r="4" fill="#222"/>
<path d="M34 60 Q48 70 62 60" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round"/>
<rect x="44" y="2" width="8" height="14" fill="#3373cc"/><circle cx="48" cy="4" r="5" fill="#ffbf00"/>
<text x="48" y="92" font-size="12" text-anchor="middle" fill="#3373cc" font-family="sans-serif">TURBO 2.0</text></svg>"""
STAGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
<rect width="480" height="360" fill="#f4f7ff"/></svg>"""


def costume(svg, name, cx, cy):
    data = svg.encode()
    md5 = hashlib.md5(data).hexdigest()
    return {"assetId": md5, "name": name, "md5ext": md5 + ".svg", "dataFormat": "svg",
            "rotationCenterX": cx, "rotationCenterY": cy}, (md5 + ".svg", data)


def write_sb3(project, path, sprite_name="Turbo"):
    c1, f1 = costume(SPRITE_SVG, "turbo", 48, 48)
    c2, f2 = costume(STAGE_SVG, "backdrop", 240, 180)
    targets = project.to_targets([c1], c2, sprite_name)
    pj = {"targets": targets, "monitors": getattr(project, "monitors", []), "extensions": [],
          "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "turbo2-builder"}}
    txt = json.dumps(pj, separators=(",", ":"))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", txt)
        z.writestr(*f1)
        z.writestr(*f2)
    return pj, len(txt)
