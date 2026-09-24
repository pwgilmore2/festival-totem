"""Identify actual HUB75 RGB color order on both chained 64x32 panels.

Copy to CIRCUITPY/code.py. Three small squares per panel are requested in
software as red, green, blue from left to right; report the visible colors.
"""

import board
import displayio
import framebufferio
import rgbmatrix
import time

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=128, height=32, bit_depth=1,
    addr_pins=board.MTX_ADDRESS[:4], tile=1,
    **board.MTX_COMMON
)
display = framebufferio.FramebufferDisplay(matrix)
bitmap = displayio.Bitmap(128, 32, 4)
palette = displayio.Palette(4)
palette[0] = 0x000000
palette[1] = 0xFF0000
palette[2] = 0x00FF00
palette[3] = 0x0000FF
for panel_start in (0, 64):
    for color, square_start in ((1, 4), (2, 20), (3, 36)):
        for y in range(4, 12):
            for x in range(panel_start + square_start, panel_start + square_start + 8):
                bitmap[x, y] = color
group = displayio.Group()
group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = group
print("Software requested RED GREEN BLUE, left-to-right on each panel")
while True:
    time.sleep(1)
