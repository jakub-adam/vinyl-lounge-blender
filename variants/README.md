# Variants (intermediate + simple)

Both use `../lib/mk.py` and `../lib/tex.py` (copy or symlink `lib/` next to these scripts).

| Variant | Build | Notes |
|---|---|---|
| intermediate | `python intermediate_textures.py OUT ../textures` then `python intermediate_build.py OUT [--render]`, `python intermediate_inspo.py OUT` | living room with record player, ~21k quads |
| simple (final, on `main`) | copy `wood_floor_*`, `oak_*`, `album_1.jpg` into `OUT/textures`, then `python simple_build.py OUT [--render]`, `python simple_inspo.py OUT`, `python final_verify.py OUT` | exactly 4 furniture + 4 grabbables, window, wall TV, ~9.3k quads, .blend/.glb/.fbx |
