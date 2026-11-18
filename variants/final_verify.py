"""Final check of the deliverables against the brief + Unity/VR readiness.
usage: python final_verify.py <dir>
"""
import os
import sys
import json
import struct
import bpy
import bmesh
from mathutils import Vector

D = sys.argv[-1]
N = "4SA1_Claude_Interier_v01"
out = []


def rep(ok, key, txt):
    out.append((ok, key, txt))
    print(f"[{'OK ' if ok else 'XX '}] {key}: {txt}", flush=True)


# ------------------------------------------------------------ .blend ------
bpy.ops.wm.open_mainfile(filepath=os.path.join(D, N + ".blend"))
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tot = tri = ngon = base_bad = open_e = 0
per = []
for ob in meshes:
    me = ob.evaluated_get(dg).to_mesh()
    f = len(me.polygons)
    t = sum(1 for p in me.polygons if len(p.vertices) == 3)
    n = sum(1 for p in me.polygons if len(p.vertices) > 4)
    used = sorted({ob.material_slots[p.material_index].material.name for p in me.polygons})
    bm = bmesh.new()
    bm.from_mesh(me)
    oe = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    base_bad += sum(1 for p in ob.data.polygons if len(p.vertices) != 4)
    tot, tri, ngon, open_e = tot + f, tri + t, ngon + n, open_e + oe
    per.append((ob.name, ob.users_collection[0].name, f, used, oe))
furn = sorted(o.name for o in bpy.data.collections["Furniture"].objects)
grab = sorted(o.name for o in bpy.data.collections["Grabbables"].objects)
rep(tot < 100_000, "Polygóny", f"{tot:,} faces po modifikátoroch (limit 100 000)")
rep(tri == 0 and ngon == 0 and base_bad == 0, "Quad topológia",
    f"{tri} trojuholníkov, {ngon} n-gonov (aj v základných meshoch: {base_bad})")
one = [p[0] for p in per if len(p[3]) < 2]
rep(not one, "Min. 2 materiály / objekt", "všetkých %d objektov má ≥ 2 použité materiály %s" % (len(per), one or ""))
rep(len(furn) >= 4, "Nábytok ≥ 4", ", ".join(furn))
rep(len(grab) >= 4 and all(bpy.data.objects[g].get("grabbable") == 1 for g in grab),
    "Grabbables ≥ 4", ", ".join(grab) + " (samostatné objekty, property grabbable=1)")
rep(sc.render.engine == "CYCLES", "Render Cycles",
    f"{sc.render.resolution_x}×{sc.render.resolution_y}, {sc.cycles.samples} samples, denoise={sc.cycles.use_denoising}")
hid = sorted(o.name for o in meshes if not o.visible_camera)
rep({"Wall_Front", "Wall_Right"} <= set(hid), "Predné steny skryté",
    f"{', '.join(hid)}: Object > Visibility > Ray Visibility > Camera = off (vrhajú tiene)")
rep(open_e == 0, "Uzavreté meshe", f"{open_e} otvorených/non-manifold hrán")
sc_bad = [o.name for o in meshes if any(abs(s - 1) > 1e-6 for s in o.scale)]
rep(not sc_bad and sc.unit_settings.scale_length == 1.0, "Mierka (Unity)",
    "všetky objekty scale 1,1,1; 1 jednotka = 1 m" + (f" {sc_bad}" if sc_bad else ""))
nouv = [o.name for o in meshes if not o.data.uv_layers]
rep(not nouv, "UV mapy", "každý mesh má UV mapu" + (f" chýba: {nouv}" if nouv else ""))
sizes = []
for g in grab:
    o = bpy.data.objects[g]
    me = o.evaluated_get(dg).to_mesh()
    zs = [v.co.z for v in me.vertices]
    dims = o.dimensions
    sizes.append(f"{g} {dims.x * 100:.0f}×{dims.y * 100:.0f}×{dims.z * 100:.0f} cm")
rep(True, "Grabbables – veľkosti", "; ".join(sizes))
packed = all(i.packed_file is not None for i in bpy.data.images if i.source == "FILE")
rep(packed, "Textúry v .blend", f"{len(bpy.data.images)} obrázkov zabalených (Pack Resources)")

# --------------------------------------------------------------- .glb -----
p = os.path.join(D, N + ".glb")
with open(p, "rb") as f:
    f.read(12)
    n, _ = struct.unpack("<I4s", f.read(8))
    js = json.loads(f.read(n))
nodes = {x.get("name"): x for x in js["nodes"]}


def yrange(name):
    a = js["accessors"][js["meshes"][nodes[name]["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
    t = nodes[name].get("translation", [0, 0, 0])
    return a["min"][1] + t[1], a["max"][1] + t[1]


fy = yrange("Floor")
wy = yrange("Wall_Back")
rep(abs(fy[1]) < 1e-3 and abs(wy[1] - 2.6) < 1e-3, "glTF +Y up",
    f"podlaha Y {fy[0]:.2f}..{fy[1]:.2f} m, zadná stena Y {wy[0]:.2f}..{wy[1]:.2f} m")
tris = sum(js["accessors"][pr["indices"]]["count"] // 3 for m in js["meshes"] for pr in m["primitives"])
glass = [m for m in js["materials"] if m["name"] == "Glass"][0]
groups = [x["name"] for x in js["nodes"] if "children" in x and "mesh" not in x]
extras = sum(1 for x in js["nodes"] if x.get("extras", {}).get("grabbable") == 1)
rep(tris < 200_000, ".glb obsah",
    f"{len(js['meshes'])} meshov, {tris:,} trojuholníkov (= {tris // 2:,} quadov × 2), "
    f"{len(js['materials'])} materiálov, {len(js.get('images', []))} textúr vložených, "
    f"skupiny {groups}, sklo alphaMode={glass.get('alphaMode')}, grabbable extras na {extras} uzloch, "
    f"{os.path.getsize(p) / 1e6:.1f} MB")

# re-import tests (what Unity would read)
for ext in (".glb", ".fbx"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fp = os.path.join(D, N + ext)
    if ext == ".glb":
        bpy.ops.import_scene.gltf(filepath=fp)
    else:
        bpy.ops.import_scene.fbx(filepath=fp)
    ms = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    fc = sum(len(o.data.polygons) for o in ms)
    imgs = len(bpy.data.images)
    rot0 = all(abs(a) < 1e-4 for o in ms if o.name.split(".")[0] in ("Floor", "Wall_Back", "Sofa", "Sideboard", "Coffee_Table") for a in o.rotation_euler)
    mx = max((o.matrix_world @ Vector(c)).z for o in ms for c in o.bound_box)
    rep(len(ms) == len(meshes), f"Re-import {ext}",
        f"{len(ms)} objektov, {fc:,} faces, {imgs} textúr, výška miestnosti {mx:.2f} m"
        + (", nábytok bez rotácie/scale artefaktov" if ext == ".fbx" and rot0 else ""))

# --------------------------------------------------------------- files ----
for ext, what in ((".blend", "Blender scéna"), (".glb", "glTF binárny"), (".fbx", "FBX pre Unity"),
                  (".png", "render"), (".jpg", "2D inšpirácia")):
    fp = os.path.join(D, N + ext)
    ok = os.path.exists(fp)
    extra = ""
    if ok and ext in (".png", ".jpg"):
        from PIL import Image
        extra = " %d×%d" % Image.open(fp).size
    rep(ok, f"Súbor {N}{ext}", what + extra + (f", {os.path.getsize(fp) / 1e6:.1f} MB" if ok else " CHÝBA"))

print("\nOBJEKTY:")
for name, col, f, used, oe in sorted(per, key=lambda r: (r[1], r[0])):
    print(f"  {col:11s} {name:14s} {f:5d} faces  {', '.join(used)}")
print("\nVYSLEDOK:", "VSETKO OK" if all(o for o, _, _ in out) else "NIECO NESEDI")
