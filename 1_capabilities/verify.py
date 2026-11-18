"""verify.py - checks the deliverables against the brief and writes out/verification.md

    python verify.py
"""
import os
import sys
import json
import struct

import bpy
import bmesh

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
BASENAME = "4SA1_Claude_Interier_v01"


def glb_json(path):
    with open(path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", "not a GLB"
        clen, ctype = struct.unpack("<I4s", f.read(8))
        return version, json.loads(f.read(clen))


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, BASENAME + ".blend"))
    sc = bpy.context.scene
    rows, checks = [], []
    tot = tris = ngons = 0
    one_mat = []
    open_edges = {}
    for ob in sorted(bpy.data.objects, key=lambda o: o.name):
        if ob.type != "MESH":
            continue
        me = ob.data
        nf = len(me.polygons)
        nt = sum(1 for p in me.polygons if len(p.vertices) == 3)
        nn = sum(1 for p in me.polygons if len(p.vertices) > 4)
        used = sorted({me.materials[p.material_index].name for p in me.polygons})
        bm = bmesh.new()
        bm.from_mesh(me)
        nm = sum(1 for e in bm.edges if not e.is_manifold)
        bm.free()
        tot += nf
        tris += nt
        ngons += nn
        if len(used) < 2:
            one_mat.append(ob.name)
        if nm:
            open_edges[ob.name] = nm
        rows.append((ob.name, ob.get("category", "-"), nf, len(used), ", ".join(used)))
    furn = [r[0] for r in rows if r[1] == "furniture"]
    grab = [r[0] for r in rows if r[1] == "grabbable"]
    hidden = [o.name for o in bpy.data.objects if o.type == "MESH" and not o.visible_camera]

    def check(ok, text):
        checks.append(("PASS" if ok else "FAIL", text))

    check(tot < 100_000, f"Total faces {tot:,} < 100,000")
    check(tris == 0 and ngons == 0, f"Quad-only topology: {tris} triangles, {ngons} n-gons")
    check(not one_mat, "Every mesh object uses >= 2 materials" + (f" (violations: {one_mat})" if one_mat else ""))
    check(len(furn) >= 4, f"Furniture objects: {len(furn)} (>= 4)")
    check(len(grab) >= 4, f"Grabbable objects: {len(grab)} (>= 4), tagged with custom property grabbable=1")
    check(sc.render.engine == "CYCLES", f"Render engine: {sc.render.engine}")
    check({"ARCH_Wall_Front", "ARCH_Wall_Right"} <= set(hidden),
          f"Front walls hidden from camera (Object > Visibility > Camera off): {', '.join(hidden)}")
    check(not open_edges, "All meshes closed (no non-manifold edges)" +
          (f": {open_edges}" if open_edges else ""))

    glb = os.path.join(OUT, BASENAME + ".glb")
    ver, js = glb_json(glb)
    nodes = {n.get("name"): n for n in js.get("nodes", [])}
    ceil = nodes.get("ARCH_Ceiling")
    prim = js["meshes"][ceil["mesh"]]["primitives"][0]
    acc = js["accessors"][prim["attributes"]["POSITION"]]
    ymin, ymax = acc["min"][1], acc["max"][1]
    check(abs(ymin - 3.0) < 1e-3 and abs(ymax - 3.12) < 1e-3,
          f"glTF is +Y up: ceiling slab spans Y {ymin:.2f}..{ymax:.2f} m in the .glb")
    gl_grab = [n for n, d in nodes.items() if n and n.startswith("GRAB_") and d.get("extras", {}).get("grabbable") == 1]
    check(len(gl_grab) == len(grab), f"glTF extras carry grabbable=1 on {len(gl_grab)} nodes")
    check(len(js.get("materials", [])) >= 20, f"glTF materials exported: {len(js.get('materials', []))}, "
          f"images: {len(js.get('images', []))}, glb size {os.path.getsize(glb) / 1e6:.1f} MB")

    files = sorted(f for f in os.listdir(OUT) if f.startswith(BASENAME))
    for ext in (".blend", ".glb", ".png", ".jpg"):
        check(BASENAME + ext in files, f"Deliverable {BASENAME}{ext} present")

    lines = ["# Verification report", "", f"Blender {bpy.app.version_string}", "",
             "| Result | Check |", "|---|---|"]
    lines += [f"| {r} | {t} |" for r, t in checks]
    lines += ["", "## Objects", "", "| Object | Category | Faces | Materials (#) | Materials |",
              "|---|---|---:|---:|---|"]
    lines += [f"| {n} | {c} | {f:,} | {k} | {m} |" for n, c, f, k, m in rows]
    lines += ["", f"**Total: {len(rows)} mesh objects, {tot:,} faces (all quads).**", ""]
    with open(os.path.join(OUT, "verification.md"), "w") as f:
        f.write("\n".join(lines))
    for r, t in checks:
        print(f"[{r}] {t}")
    sys.exit(0 if all(r == "PASS" for r, _ in checks) else 1)


if __name__ == "__main__":
    main()
