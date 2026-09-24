"""Check physical RGB correction with small stable squares on both panels."""

import board
import displayio
import framebufferio
import rgbmatrix
import time

displayio.release_displays()
pins = dict(board.MTX_COMMON)
r1, g1, b1, r2, g2, b2 = pins["rgb_pins"]
pins["rgb_pins"] = (r1, b1, g1, r2, b2, g2)
matrix = rgbmatrix.RGBMatrix(
    width=128, height=32, bit_depth=1,
    addr_pins=board.MTX_ADDRESS[:4], tile=1, **pins
)
display = framebufferio.FramebufferDisplay(matrix)
bitmap = displayio.Bitmap(128, 32, 4)
palette = displayio.Palette(4)
palette[0] = 0
palette[1] = 0xFF0000
palette[2] = 0x00FF00
palette[3] = 0x0000FF
for start in (0, 64):
    for index, color in enumerate((1, 2, 3)):
        for y in range(4, 12):
            for x in range(start + 4 + index * 16, start + 12 + index * 16):
                bitmap[x, y] = color
group = displayio.Group()
group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
display.root_group = group
print("Corrected RGB test: red green blue on both panels")
while True:
    time.sleep(1)
