"""Simple version: exactly the minimum the brief asks for, nothing extra.

4 furniture (sofa, armchair, coffee table, sideboard), 4 grabbables (mug, book,
pillow, record sleeve), floor + 4 walls (front + right hidden from camera),
rounded shapes (bevel / soft cushions) so it does not look blocky.
Reuses the part recipes and materials of intermediate_build.py.

usage: python simple_build.py <outdir> [--render]   (textures in <outdir>/textures)
"""
import os
import sys
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy                                   # noqa: E402
from mathutils import Vector                 # noqa: E402
import intermediate_build as ib              # noqa: E402
from lib import mk                           # noqa: E402
from lib.mk import box, lathe                # noqa: E402

OUT = ib.OUT
NAME = ib.NAME
RW, RD, RH, WT = 4.5, 4.0, 2.6, 0.12
WIN = (1.5, 2.8, 0.9, 2.1)                   # window in the left wall: y0, y1, z0, z1


def room():
    f = box(RW + 2 * WT, RD + 2 * WT, 0.1, mat="Wood_Floor", uv=("box", 1.6, 0)).bake()
    f.by_normal(lambda n, c: n[2] > 0.9, "Wood_Floor", "Concrete").move(RW / 2, RD / 2, -0.05)
    ib.obj("Floor", [f], col="Room")
    walls = [("Wall_Back", (RW + 2 * WT, WT), (RW / 2, RD + WT / 2), (RW, 0.015), (RW / 2, RD - 0.0075), False),
             ("Wall_Left", (WT, RD), (-WT / 2, RD / 2), (0.015, RD), (0.0075, RD / 2), False),
             ("Wall_Front", (RW + 2 * WT, WT), (RW / 2, -WT / 2), (RW, 0.015), (RW / 2, 0.0075), True),
             ("Wall_Right", (WT, RD), (RW + WT / 2, RD / 2), (0.015, RD), (RW - 0.0075, RD / 2), True)]
    walls = [w for w in walls if w[0] != "Wall_Left"]
    hp, hf = ib.wall_with_hole(RD, RH, WIN[0], WIN[1], WIN[2], WIN[3])
    lw = ib.solidify2d(hp, hf, WT, mat="Wall_Paint").rot("z", 90)
    sk = box(0.015, RD, 0.08, mat="White_Paint").move(0.0075, RD / 2, 0.04)
    ib.obj("Wall_Left", [lw, sk], col="Room")
    y0, y1, z0, z1 = WIN
    fw, xc, yc, zc = 0.05, -WT / 2, (y0 + y1) / 2, (z0 + z1) / 2
    e = 0.012                                # frame reaches 1 cm into the wall; depths differ so no faces coincide
    frame = [box(0.06, fw + e, z1 - z0 + 2 * e, mat="White_Paint").move(xc, y0 + fw / 2 - e / 2, zc),
             box(0.06, fw + e, z1 - z0 + 2 * e, mat="White_Paint").move(xc, y1 - fw / 2 + e / 2, zc),
             box(0.056, y1 - y0, fw + e, mat="White_Paint").move(xc, yc, z0 + fw / 2 - e / 2),
             box(0.056, y1 - y0, fw + e, mat="White_Paint").move(xc, yc, z1 - fw / 2 + e / 2),
             box(0.05, 0.04, z1 - z0, mat="White_Paint").move(xc, yc, zc),
             box(0.008, y1 - y0 - 0.06, z1 - z0 - 0.06, mat="Glass").move(xc, yc, zc)]
    ob = ib.obj("Window", frame, col="Room", bevel=0.003)
    ob.visible_shadow = False                # glass would block the sun
    c = box(RW + 2 * WT, RD + 2 * WT, 0.1, mat="Ceiling").move(RW / 2, RD / 2, RH + 0.05)
    lamp = lathe([(0.16, RH - 0.001), (0.16, RH - 0.025), (0.14, RH - 0.04)], m=6, mat="Ceiling_Light").move(RW / 2, RD / 2, 0)
    ob = ib.obj("Ceiling", [c, lamp], col="Room")
    ob.hide_render = True                    # closes the room in Unity/VR, render stays open-top
    for name, size, pos, sk, skp, hidden in walls:
        w = box(size[0], size[1], RH, mat="Wall_Paint").move(pos[0], pos[1], RH / 2)
        s = box(sk[0], sk[1], 0.08, mat="White_Paint").move(skp[0], skp[1], 0.04)
        ob = ib.obj(name, [w, s], col="Room")
        if hidden:
            ob.visible_camera = False        # front walls hidden in the render


def coffee_table():
    P = [box(1.0, 0.55, 0.035, mat="Oak").bake().move(0, 0, 0.4)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.append(lathe([(0.016, 0.0), (0.016, 0.383)], m=2, mat="Black_Metal").move(sx * 0.45, sy * 0.22, 0))
    return P


def sideboard():
    L, D, z0, z1 = 1.4, 0.45, 0.12, 0.62
    P = [box(L, D, z1 - z0, mat="Oak").bake().move(0, 0, (z0 + z1) / 2)]
    for sx in (-1, 1):
        P.append(box(L / 2 - 0.03, 0.015, z1 - z0 - 0.06, mat="Green_Paint").move(sx * (L / 4 - 0.005), -D / 2 - 0.006, (z0 + z1) / 2))
        for sy in (-1, 1):
            P.append(lathe([(0.015, 0.0), (0.02, z0)], m=2, mat="Oak").move(sx * (L / 2 - 0.08), sy * (D / 2 - 0.07), 0))
    return P


def main():
    ib.MAT.update({                          # plain colours instead of fabric textures
        "Fabric_Sofa": (None, (0.36, 0.42, 0.33), 0.9, 0, dict(sheen=0.5)),
        "Fabric_Chair": (None, (0.55, 0.25, 0.15), 0.9, 0, dict(sheen=0.5)),
        "Fabric_Pillow": (None, (0.78, 0.55, 0.15), 0.9, 0, dict(sheen=0.5)),
        "TV_Screen": (None, (0.01, 0.01, 0.012), 0.06, 0, {}),
        "Black_Plastic": (None, (0.03, 0.03, 0.03), 0.45, 0, {}),
    })
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mk.set_material_resolver(ib.get_mat, ib.tile)
    sc = bpy.context.scene
    for n in ("Room", "Furniture", "Grabbables", "Lights"):
        c = bpy.data.collections.new(n)
        sc.collection.children.link(c)
        ib.COL[n] = c
    room()

    # wall decoration: TV above the sideboard
    tv = box(1.25, 0.045, 0.72, mat="Black_Plastic").bake()
    tv.by_normal(lambda n, c: n[1] < -0.9, "TV_Screen", "Black_Plastic")
    ib.obj("TV", [tv], (2.0, RD - 0.035, 1.38), 0, col="Room", bevel=0.004)

    # furniture (4)
    ib.obj("Sideboard", sideboard(), (2.0, RD - 0.235, 0), 0, bevel=0.004)
    ib.obj("Sofa", ib.sofa(W=2.0), (2.0, 1.15, 0), 180)
    ib.obj("Coffee_Table", coffee_table(), (2.0, 2.4, 0), 0, bevel=0.004)
    ib.obj("Armchair", ib.sofa(W=0.85, D=0.82, fabric="Fabric_Chair", seats=1), (3.75, 2.45, 0), -80)

    # grabbables (4)
    top = 0.4175
    ib.obj("Mug", ib.mug(), (1.75, 2.3, top), 20, col="Grabbables")
    ib.obj("Book", ib.book(0.17, 0.24, 0.03, "Book_2"), (2.25, 2.45, top), -10, col="Grabbables")
    pl = ib.obj("Pillow", ib.pillow(), (2.65, 1.14, 0.70), 0, col="Grabbables")
    pl.rotation_euler = (math.radians(70), 0, math.radians(195))
    rec = ib.obj("Record_Sleeve", ib.sleeve("Album_1", disc=False), (2.5, RD - 0.55, 0), 0, col="Grabbables")
    rec.rotation_euler = (math.radians(-14), 0, 0)

    for ob in ib.COL["Grabbables"].objects:
        ob["grabbable"] = 1
    for ob in ib.COL["Furniture"].objects:
        ob["furniture"] = 1
    g = bpy.data.materials["Glass"].node_tree.nodes["Principled BSDF"]
    g.inputs["Alpha"].default_value = 0.3   # glTF alphaMode BLEND -> transparent in Unity

    # light + camera
    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy, ld.color, ld.angle = 4.0, (1.0, 0.92, 0.82), math.radians(2)
    sun = bpy.data.objects.new("Sun", ld)
    sun.location = (0, -3, 6)
    sun.rotation_euler = Vector((0.35, 0.55, -0.75)).to_track_quat("-Z", "Y").to_euler()
    ib.COL["Lights"].objects.link(sun)
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    sc.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.6, 0.7, 0.85, 1)
    bg.inputs["Strength"].default_value = 0.8

    cd = bpy.data.cameras.new("Camera")
    cd.lens = 30
    cam = bpy.data.objects.new("Camera", cd)
    cam.location = (5.2, -1.7, 2.45)
    cam.rotation_euler = (Vector((1.8, 2.8, 0.8)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(cam)
    sc.camera = cam

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 128
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.filepath = "//" + NAME + ".png"

    dg = bpy.context.evaluated_depsgraph_get()
    tot = bad = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            me = ob.evaluated_get(dg).to_mesh()
            tot += len(me.polygons)
            bad += sum(1 for p in me.polygons if len(p.vertices) != 4)
            used = {ob.material_slots[p.material_index].material.name for p in me.polygons}
            print(f"  {ob.name:14s} {len(me.polygons):6d}  {len(used)} mats")
    print("TOTAL faces", tot, "non-quads", bad)

    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"), compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, NAME + ".glb"), export_format="GLB",
                              export_yup=True, export_apply=True, export_tangents=True,
                              export_extras=True, export_hierarchy_full_collections=True,
                              export_cameras=False, export_lights=False)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, NAME + ".fbx"), object_types={"MESH"},
                             use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True,
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
                             axis_forward="-Z", axis_up="Y", bake_space_transform=True,
                             path_mode="COPY", embed_textures=True, use_custom_props=True,
                             add_leaf_bones=False, bake_anim=False)
    if "--render" in sys.argv:
        bpy.ops.render.render(write_still=True)
    print("done")


if __name__ == "__main__":
    main()
