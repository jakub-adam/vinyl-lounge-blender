"""mats.py - glTF-safe material library (Principled BSDF + image textures).

Every material is a single Principled BSDF fed only by Image Texture nodes
(colour / roughness / normal map), so the glTF exporter can translate it 1:1
(baseColor, metallicRoughness, normal, emissive, transmission, sheen, clearcoat).
Materials are created lazily the first time a mesh asks for them.
"""
import os
import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "textures")

# name: spec
#   tex      : texture set prefix in ./textures (col/rough/nrm files)
#   tile     : metres per texture repeat for box-projected UVs
#   color    : RGBA when no colour texture
#   rough    : roughness value when no roughness texture
#   nrm      : normal map strength
#   metal, transmission, ior, emission (rgb), estrength, sheen, coat, alpha
MATS = {
    # architecture
    "parquet":         dict(tex="parquet", tile=0.7, nrm=0.6),
    "plaster":         dict(tex="plaster", tile=1.6, nrm=0.5),
    "plaster_ceiling": dict(tex="plaster_ceiling", tile=1.6, nrm=0.3),
    "paint_green":     dict(tex="paint_green", tile=0.6, nrm=0.3, coat=0.15),
    "paint_white":     dict(color=(0.86, 0.84, 0.80, 1), rough=0.55),
    "section":         dict(color=(0.07, 0.07, 0.075, 1), rough=0.95),   # cut faces (dollhouse poche)
    "glass":           dict(color=(0.95, 0.97, 0.96, 1), rough=0.02, transmission=1.0, ior=1.45),
    "backdrop":        dict(tex="backdrop", tile=None, emission_tex=True, estrength=1.3, rough=1.0),
    # woods / stone / metals
    "walnut":          dict(tex="walnut", tile=0.6, nrm=0.35, coat=0.25),
    "oak":             dict(tex="oak", tile=0.5, nrm=0.35),
    "marble":          dict(tex="marble", tile=0.9, nrm=0.2, coat=0.4),
    "brass":           dict(tex="brass", tile=0.4, nrm=0.15, metal=1.0),
    "alu":             dict(tex="alu", tile=0.3, nrm=0.15, metal=1.0),
    "blackmetal":      dict(tex="blackmetal", tile=0.4, nrm=0.15, metal=0.6),
    # textiles
    "boucle":          dict(tex="boucle", tile=0.35, nrm=1.0, sheen=0.6),
    "leather":         dict(tex="leather", tile=0.45, nrm=0.6, coat=0.1),
    "rug":             dict(tex="rug", tile=None, nrm=0.6, sheen=0.4),
    "rug_binding":     dict(color=(0.42, 0.16, 0.10, 1), rough=0.9, sheen=0.4),
    "grill":           dict(tex="grill", tile=0.18, nrm=0.6, sheen=0.3),
    "cloth_teal":      dict(tex="cloth_teal", tile=0.12, nrm=0.4),
    "cloth_ochre":     dict(tex="cloth_ochre", tile=0.12, nrm=0.4),
    "cloth_wine":      dict(tex="cloth_wine", tile=0.12, nrm=0.4),
    "felt":            dict(color=(0.03, 0.03, 0.035, 1), rough=0.95, sheen=0.5),
    # ceramics / paper / misc
    "ceramic_cream":   dict(tex="ceramic_cream", tile=0.25, nrm=0.2, coat=0.6),
    "terracotta":      dict(tex="terracotta", tile=0.3, nrm=0.4),
    "paper":           dict(tex="paper", tile=0.3, nrm=0.2),
    "pages":           dict(color=(0.93, 0.90, 0.82, 1), rough=0.85),
    "cardboard":       dict(tex="cardboard", tile=0.3, nrm=0.3),
    "rubber":          dict(tex="rubber", tile=0.2, nrm=0.2),
    "leaf":            dict(tex="leaf", tile=0.25, nrm=0.4, coat=0.2),
    "stem":            dict(color=(0.20, 0.30, 0.12, 1), rough=0.6),
    "cactus":          dict(color=(0.16, 0.32, 0.20, 1), rough=0.55, coat=0.2),
    "soil":            dict(tex="soil", tile=0.25, nrm=0.6),
    "coffee":          dict(color=(0.06, 0.03, 0.015, 1), rough=0.05, coat=1.0),
    "vinyl_black":     dict(color=(0.012, 0.012, 0.014, 1), rough=0.22, coat=0.6),
    "plastic_black":   dict(color=(0.02, 0.02, 0.022, 1), rough=0.35),
    "poster":          dict(tex="poster", tile=None, rough=0.7),
    # light emitters
    "lamp_glow":       dict(color=(0.95, 0.92, 0.86, 1), rough=0.5, emission=(1.0, 0.78, 0.52), estrength=5.0,
                            transmission=0.0),
    "bulb":            dict(color=(1, 1, 1, 1), rough=0.2, emission=(1.0, 0.75, 0.45), estrength=25.0),
    "led_red":         dict(color=(0.5, 0.02, 0.02, 1), rough=0.3, emission=(1.0, 0.1, 0.05), estrength=8.0),
}
for i in range(6):
    MATS[f"cover{i}"] = dict(tex=f"cover{i}", tile=None, rough=0.55, coat=0.15)
for i in range(3):
    MATS[f"vinyl{i}"] = dict(tex=f"vinyl{i}", tile=None, nrm=0.5, coat=0.5)


def tile_of(name):
    spec = MATS.get(name, {})
    return spec.get("tile") or 1.0


def _img(fname, noncolor):
    path = os.path.join(TEX, fname)
    if not os.path.exists(path):
        return None
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return img


def _find(prefix, kind):
    for ext in (".jpg", ".png"):
        f = f"{prefix}_{kind}{ext}"
        if os.path.exists(os.path.join(TEX, f)):
            return f
    return None


def make(name):
    spec = MATS.get(name)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if spec is None:
        print("WARNING: unknown material", name)
        bsdf.inputs["Base Color"].default_value = (1, 0, 1, 1)
        return m
    I = bsdf.inputs
    y = 300
    tex = spec.get("tex")
    if tex:
        f = _find(tex, "col")
        if f:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = _img(f, False)
            n.location = (-500, y)
            n.label = "color"
            nt.links.new(n.outputs["Color"], I["Base Color"])
            if spec.get("emission_tex"):
                nt.links.new(n.outputs["Color"], I["Emission Color"])
                I["Emission Strength"].default_value = spec.get("estrength", 1.0)
            y -= 300
        f = _find(tex, "rough")
        if f:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = _img(f, True)
            n.location = (-500, y)
            n.label = "roughness"
            nt.links.new(n.outputs["Color"], I["Roughness"])
            y -= 300
        f = _find(tex, "nrm")
        if f and spec.get("nrm", 0) > 0:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = _img(f, True)
            n.location = (-500, y)
            n.label = "normal"
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (-200, y)
            nm.inputs["Strength"].default_value = spec["nrm"]
            nt.links.new(n.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], I["Normal"])
    if "color" in spec:
        I["Base Color"].default_value = spec["color"]
    if "rough" in spec and not I["Roughness"].is_linked:
        I["Roughness"].default_value = spec["rough"]
    I["Metallic"].default_value = spec.get("metal", 0.0)
    if spec.get("transmission"):
        I["Transmission Weight"].default_value = spec["transmission"]
        I["IOR"].default_value = spec.get("ior", 1.45)
    if spec.get("emission"):
        I["Emission Color"].default_value = (*spec["emission"], 1)
        I["Emission Strength"].default_value = spec.get("estrength", 1.0)
    if spec.get("sheen"):
        I["Sheen Weight"].default_value = spec["sheen"]
        I["Sheen Roughness"].default_value = 0.5
    if spec.get("coat"):
        I["Coat Weight"].default_value = spec["coat"]
        I["Coat Roughness"].default_value = 0.08
    # viewport colour = average texture tone (nice solid-mode preview)
    m.diffuse_color = spec.get("color", (0.6, 0.6, 0.6, 1))
    return m


def get(name):
    m = bpy.data.materials.get(name)
    return m if m is not None else make(name)
