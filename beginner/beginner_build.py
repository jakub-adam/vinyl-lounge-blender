"""Beginner-style minimal interior (mimics a first-time Blender student's GUI workflow).

Everything is made from default cubes (Add > Mesh > Cube), moved and scaled with
G/S (scale left unapplied), joined with Ctrl+J, flat Principled BSDF colours,
one Sun, Cycles with low samples, glTF export with defaults (+Y up).

usage: python beginner_build.py <outdir>
"""
import os
import sys
import math
import bpy
from mathutils import Vector

OUT = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else os.getcwd()
NAME = "4SA1_Claude_Interier_v01"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

MATS = {}


def mat(name, color, rough=0.5, metal=0.0, emit=None):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 1.0
    m.diffuse_color = (*color, 1)
    MATS[name] = m
    return m


def cube(name, loc, scale, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc, rotation=[math.radians(a) for a in rot])
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    ob.data.materials.append(material)
    return ob


def join(name, objs):
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs,
                                   selected_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def second_mat(ob, material, test):
    """assign material to faces whose (local) normal passes test - like selecting faces + Assign"""
    ob.data.materials.append(material)
    idx = len(ob.data.materials) - 1
    for p in ob.data.polygons:
        if test(p.normal):
            p.material_index = idx


# materials
podlaha = mat("podlaha", (0.32, 0.18, 0.08), 0.4)
sivy = mat("Material.001", (0.6, 0.6, 0.6))
stena = mat("stena", (0.85, 0.8, 0.7), 0.8)
drevo = mat("drevo", (0.45, 0.27, 0.12), 0.45)
svetle = mat("drevo svetle", (0.72, 0.55, 0.35), 0.45)
kov = mat("kov", (0.7, 0.7, 0.72), 0.3, 1.0)
matrac = mat("matrac", (0.9, 0.9, 0.88), 0.9)
biela = mat("biela", (0.92, 0.92, 0.9), 0.3)
obal = mat("obal", (0.6, 0.08, 0.08), 0.6)
papier = mat("papier", (0.95, 0.93, 0.85), 0.9)
obrazovka = mat("obrazovka", (0.02, 0.02, 0.03), 0.1, emit=(0.1, 0.2, 0.35))
modra = mat("vankus modry", (0.15, 0.3, 0.6), 0.9)
karton = mat("karton", (0.55, 0.38, 0.2), 0.8)
paska = mat("paska", (0.85, 0.75, 0.5), 0.4)

# room 4 x 4 m, 2.6 m high
p = cube("podlaha", (2, 2, -0.05), (2, 2, 0.05), sivy)
second_mat(p, podlaha, lambda n: n.z > 0.9)
w = cube("stena_zadna", (2, 4.05, 1.3), (2.1, 0.05, 1.3), sivy)
second_mat(w, stena, lambda n: n.y < -0.9)
w = cube("stena_lava", (-0.05, 2, 1.3), (0.05, 2.1, 1.3), sivy)
second_mat(w, stena, lambda n: n.x > 0.9)
w = cube("stena_predna", (2, -0.05, 1.3), (2.1, 0.05, 1.3), sivy)
second_mat(w, stena, lambda n: n.y > 0.9)
w.hide_render = True                                  # predne steny skryte v renderi
w = cube("stena_prava", (4.05, 2, 1.3), (0.05, 2.1, 1.3), sivy)
second_mat(w, stena, lambda n: n.x < -0.9)
w.hide_render = True

# --- nabytok ---
# postel
parts = [cube("ram", (0.55, 3.0, 0.15), (0.5, 1.0, 0.15), drevo),
         cube("celo", (0.55, 3.97, 0.5), (0.5, 0.03, 0.5), drevo),
         cube("matrac", (0.55, 3.0, 0.4), (0.47, 0.95, 0.1), matrac)]
join("postel", parts)
# stol
parts = [cube("doska", (2.9, 3.6, 0.73), (0.6, 0.3, 0.02), svetle)]
for x in (-0.55, 0.55):
    for y in (-0.25, 0.25):
        parts.append(cube("noha", (2.9 + x, 3.6 + y, 0.355), (0.025, 0.025, 0.355), kov))
join("stol", parts)
# stolicka
parts = [cube("sedak", (2.9, 3.0, 0.45), (0.22, 0.22, 0.02), drevo),
         cube("operadlo", (2.9, 2.8, 0.72), (0.22, 0.02, 0.2), drevo)]
for x in (-0.19, 0.19):
    for y in (-0.19, 0.19):
        parts.append(cube("noha", (2.9 + x, 3.0 + y, 0.215), (0.02, 0.02, 0.215), kov))
join("stolicka", parts)
# skrina
parts = [cube("skrina", (0.35, 1.0, 1.0), (0.3, 0.6, 1.0), biela),
         cube("uchytka", (0.66, 0.95, 1.0), (0.01, 0.01, 0.1), kov),
         cube("uchytka", (0.66, 1.05, 1.0), (0.01, 0.01, 0.1), kov)]
join("skrina", parts)

# --- veci ktore sa daju chytit ---
k = cube("kniha", (2.65, 3.6, 0.765), (0.1, 0.14, 0.015), obal, rot=(0, 0, 15))
second_mat(k, papier, lambda n: n.x > 0.9 or abs(n.y) > 0.9)
parts = [cube("notebook", (3.1, 3.55, 0.758), (0.16, 0.11, 0.008), kov),
         cube("displej", (3.1, 3.665, 0.86), (0.16, 0.005, 0.105), kov, rot=(-12, 0, 0))]
second_mat(parts[1], obrazovka, lambda n: n.y < -0.9)
join("notebook", parts)
v = cube("vankus", (0.55, 3.72, 0.56), (0.32, 0.18, 0.06), matrac)
second_mat(v, modra, lambda n: n.z > 0.9)
v.modifiers.new("Subdivision", "SUBSURF").levels = 2
v.modifiers["Subdivision"].render_levels = 2
b = cube("krabica", (1.45, 3.5, 0.12), (0.2, 0.15, 0.12), karton, rot=(0, 0, 20))
second_mat(b, paska, lambda n: n.z > 0.9)

# --- svetlo + kamera ---
bpy.ops.object.light_add(type="SUN", location=(4, -3, 5))
sun = bpy.context.active_object
sun.data.energy = 4
sun.rotation_euler = Vector((-0.45, 0.65, -0.62)).to_track_quat("-Z", "Y").to_euler()
world = bpy.data.worlds.new("World")
sc.world = world
world.color = (0.05, 0.05, 0.05)
try:
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.05, 0.05, 1)
except Exception:
    pass

bpy.ops.object.camera_add(location=(6.2, -2.7, 2.5))
cam = bpy.context.active_object
cam.data.lens = 35
cam.rotation_euler = (Vector((1.7, 2.3, 0.75)) - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam

# --- render ---
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.filepath = os.path.join(OUT, NAME + ".png")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, NAME + ".glb"), export_format="GLB",
                          export_yup=True, export_apply=True)
if "--render" in sys.argv:
    bpy.ops.render.render(write_still=True)
print("done")
