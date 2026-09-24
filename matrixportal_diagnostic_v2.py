"""Isolated first-light test using CircuitPython's built-in display modules.

Copy ONLY this file to CIRCUITPY as code.py. No third-party libraries.
"""

import board
import displayio
import framebufferio
import rgbmatrix
import time

print("DIAG: imports complete")
displayio.release_displays()
print("DIAG: creating 128x32 matrix")
matrix = rgbmatrix.RGBMatrix(
    width=128,
    height=32,
    bit_depth=1,
    addr_pins=board.MTX_ADDRESS[:4],
    tile=1,
    **board.MTX_COMMON
)
print("DIAG: matrix created")
display = framebufferio.FramebufferDisplay(matrix)
print("DIAG: display created")
bitmap = displayio.Bitmap(128, 32, 3)
palette = displayio.Palette(3)
palette[0] = 0x000000
palette[1] = 0xFF0000
palette[2] = 0x0000FF
# At bit_depth=1, low RGB values may round to black. Illuminate only
# 8x8 pixels per panel so the saturated test colors draw little current.
for y in range(8):
    for x in range(8):
        bitmap[4 + x, 4 + y] = 1
        bitmap[68 + x, 4 + y] = 2
group = displayio.Group()
group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = group
print("DIAG: red 8x8 square on first panel; blue 8x8 on second")
while True:
    time.sleep(1)
