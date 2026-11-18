"""render.py - render the saved scene with Cycles.

    python render.py [--res 1920x1080] [--samples 256] [--out path.png]
                     [--cam x,y,z --target x,y,z --lens 24] [--exposure 0]

Defaults produce the final still out/4SA1_Claude_Interier_v01.png.
"""
import os
import sys
import time
import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
BASENAME = "4SA1_Claude_Interier_v01"


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "out", BASENAME + ".blend"))
    sc = bpy.context.scene
    w, h = map(int, arg("--res", "1920x1080").split("x"))
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.cycles.samples = int(arg("--samples", "256"))
    sc.cycles.device = "CPU"
    sc.render.threads_mode = "AUTO"
    sc.view_settings.exposure = float(arg("--exposure", sc.view_settings.exposure))
    cam = sc.camera
    if arg("--cam"):
        cam.location = Vector(map(float, arg("--cam").split(",")))
    if arg("--target"):
        d = Vector(map(float, arg("--target").split(","))) - cam.location
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if arg("--lens"):
        cam.data.lens = float(arg("--lens"))
    if arg("--shift"):
        cam.data.shift_y = float(arg("--shift"))
    out = arg("--out", os.path.join(ROOT, "out", BASENAME + ".png"))
    sc.render.filepath = out
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"rendered {w}x{h} @ {sc.cycles.samples} spp in {time.time() - t:.1f}s -> {out}", flush=True)


if __name__ == "__main__":
    main()
