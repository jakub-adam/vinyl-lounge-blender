"""Check the intermediate deliverables against the brief. usage: python intermediate_verify.py <dir>"""
import os
import sys
import json
import struct
import bpy

D = sys.argv[-1]
N = "4SA1_Claude_Interier_v01"
bpy.ops.wm.open_mainfile(filepath=os.path.join(D, N + ".blend"))
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
res = []


def check(ok, txt):
    res.append(ok)
    print(("PASS " if ok else "FAIL ") + txt)


tot = nonq = 0
one = []
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    me = ob.evaluated_get(dg).to_mesh()
    tot += len(me.polygons)
    nonq += sum(1 for p in me.polygons if len(p.vertices) != 4)
    used = {ob.material_slots[p.material_index].material.name for p in me.polygons}
    if len(used) < 2:
        one.append(ob.name)
furn = [o.name for o in bpy.data.collections["Furniture"].objects if o.type == "MESH"]
grab = [o.name for o in bpy.data.collections["Grabbables"].objects if o.type == "MESH"]
check(tot <= 100_000, f"faces after modifiers: {tot:,} (limit 100,000)")
check(nonq == 0, f"quad topology after modifiers: {nonq} non-quad faces")
check(not one, f"every object has >= 2 materials {one if one else ''}")
check(len(furn) >= 4, f"furniture: {len(furn)} -> {', '.join(sorted(furn))}")
check(len(grab) >= 4, f"grabbables: {len(grab)} -> {', '.join(sorted(grab))}")
check(sc.render.engine == "CYCLES", f"render engine {sc.render.engine}, {sc.cycles.samples} spp, "
      f"{sc.render.resolution_x}x{sc.render.resolution_y}")
hid = [o.name for o in bpy.data.objects if o.type == "MESH" and not o.visible_camera]
check({"Wall_Front", "Wall_Right"} <= set(hid), f"walls hidden from camera: {hid}")
mods = sorted({m.type for o in bpy.data.objects for m in getattr(o, "modifiers", [])})
print("     live modifiers in file:", mods)
with open(os.path.join(D, N + ".glb"), "rb") as f:
    f.read(12)
    n, _ = struct.unpack("<I4s", f.read(8))
    js = json.loads(f.read(n))
nd = {x.get("name"): x for x in js["nodes"]}
acc = js["accessors"][js["meshes"][nd["Ceiling"]["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
check(abs(acc["min"][1] - 2.7) < 0.01 and abs(acc["max"][1] - 2.8) < 0.01,
      f"glb is +Y up (ceiling at Y {acc['min'][1]:.2f}..{acc['max'][1]:.2f} m)")
tris = sum(js["accessors"][p["indices"]]["count"] // 3 for m in js["meshes"] for p in m["primitives"])
print(f"     glb: {len(js['meshes'])} meshes, {tris:,} triangles (= quads x2), {len(js.get('images', []))} images")
for ext in (".blend", ".glb", ".png", ".jpg"):
    check(os.path.exists(os.path.join(D, N + ext)), f"file {N}{ext}")
print("ALL PASS" if all(res) else "SOME FAILED")
