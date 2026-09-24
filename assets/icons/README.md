# Icon Assets

Drop transparent **32x32 PNG** icon masters in this folder.

Rules:
- Canvas must be exactly 32x32 pixels.
- Preserve transparency.
- Icons render 1:1 on the LED panel; there is no runtime scaling or auto-repair.
- File names become display names. Example: `water_bottle_32x32.png` -> `Water Bottle`.
- Restart the simulator after adding/removing files. The folder becomes authoritative when it contains at least one valid PNG.

For a larger icon, put a transparent PNG in `large/` with a canvas between 1×1
and 64×32 pixels. For example `large/liquid_stranger.png` is the user's
60×28 dripping-letter logo with color added inside its original silhouette.
It renders at native size, centered on each 64×32 panel;
Orbit and Bounce use only the free margin, so a 64×32 canvas stays still.
Original 32×32 icons retain their existing motion, including edge clipping.
Keep display names unique across both folders (the filename becomes the name).

Restart the simulator after changing icons. `python tools/build_large_icons.py`
compiles the large PNGs into `large_icon_data.py` for the PIL-free CircuitPython
icon library. The MatrixPortal asset build also refreshes that module and copies
it into `matrixportal_build/`; deploy it beside `embedded_icon_library.py` (or
`runtime_icons.py`). Each added icon uses device RAM when the library loads, so
test the final set on hardware. Desktop uses the PNGs directly. The original
embedded 32×32 icon set is used on desktop when the root folder has no valid
PNGs, even if `large/` has icons. Hardware's 32×32 icons come from the
existing embedded masters.
