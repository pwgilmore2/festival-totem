# Icon Assets

Drop transparent PNG icon masters in this folder. The standard canvas is
**32×32**, but files up to **40×40** are accepted so artwork with a few extra
border pixels does not need manual cropping.

Rules:
- The filename suffix `_32x32` is only a display-name convention; the PNG's
  actual dimensions determine whether it loads.
- Preserve transparency.
- Icons render 1:1, centered by the canvas dimensions. Pixels beyond the
  panel edges are clipped; no scaling or automatic cropping is applied.
- File names become display names. Example: `water_bottle_32x32.png` -> `Water Bottle`.
- In the desktop simulator, **Reload Library** updates the icon list and phone
  previews. The root folder becomes authoritative for standard icons when it
  contains at least one valid PNG.

For a larger icon, put a transparent PNG in `large/` with a canvas up to
**72×40** pixels (nominal 64×32 plus eight pixels in each dimension). For
example `large/liquid_stranger.png` is the user's
60×28 dripping-letter logo with color added inside its original silhouette.
It renders at native size, centered on each 64×32 panel. Orbit and Bounce use
the free margin when available; a full-size or slightly oversized icon can
clip another one or two pixels as it moves. Original 32×32 icons keep their
existing motion, including edge clipping.
Keep display names unique across both folders (the filename becomes the name).

`python tools/build_large_icons.py`
compiles the large PNGs into `large_icon_data.py` for the PIL-free CircuitPython
icon library. The MatrixPortal asset build also refreshes that module and copies
it into `matrixportal_build/`; deploy it beside `embedded_icon_library.py` (or
`runtime_icons.py`). Each added icon uses device RAM when the library loads, so
test the final set on hardware. Desktop uses the PNGs directly. The original
embedded 32×32 icon set is used on desktop when the root folder has no valid
PNGs, even if `large/` has icons. Hardware's 32×32 icons come from the
existing embedded masters.
