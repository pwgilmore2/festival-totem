# Icon Assets

Drop transparent **32x32 PNG** icon masters in this folder.

Rules:
- Canvas must be exactly 32x32 pixels.
- Preserve transparency.
- Icons render 1:1 on the LED panel; there is no runtime scaling or auto-repair.
- File names become display names. Example: `water_bottle_32x32.png` -> `Water Bottle`.
- Restart the simulator after adding/removing files. The folder becomes authoritative when it contains at least one valid PNG.

The embedded icon set is only used as a fallback when this folder has no valid PNGs.
