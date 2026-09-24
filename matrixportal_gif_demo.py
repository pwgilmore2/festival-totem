"""Minimal mirrored GIF playback test for two chained MatrixPortal S3 panels.

Copy this file to CIRCUITPY/code.py and the two small prepared GIFs to
CIRCUITPY/media/. This uses native gifio and displayio, no external libraries.
"""

import board
import displayio
import framebufferio
import gc
import gifio
import rgbmatrix
import time


FILES = ("/media/test_orbit.gif", "/media/test_wave.gif")

displayio.release_displays()
pins = dict(board.MTX_COMMON)
r1, g1, b1, r2, g2, b2 = pins["rgb_pins"]
pins["rgb_pins"] = (r1, b1, g1, r2, b2, g2)
matrix = rgbmatrix.RGBMatrix(
    width=128, height=32, bit_depth=1,
    addr_pins=board.MTX_ADDRESS[:4], tile=1, **pins
)
display = framebufferio.FramebufferDisplay(matrix)
group = displayio.Group()
display.root_group = group
shader = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED)


def open_gif(index):
    gif = gifio.OnDiskGif(FILES[index])
    delay = max(0.04, gif.next_frame())
    # Both TileGrids share one decoded bitmap; only one GIF decoder runs.
    group.append(displayio.TileGrid(gif.bitmap, pixel_shader=shader, x=0))
    group.append(displayio.TileGrid(gif.bitmap, pixel_shader=shader, x=64))
    return gif, delay


print("GIF demo: two mirrored panels; RBG corrected; bit depth 1")
index = 0
gif, delay = open_gif(index)
now = time.monotonic()
next_frame = now + delay
next_asset = now + 12
next_report = now + 5
frames = 0
max_decode_ms = 0.0
while True:
    now = time.monotonic()
    if now >= next_asset:
        group.pop()
        group.pop()
        gif.deinit()
        index = (index + 1) % len(FILES)
        gc.collect()
        gif, delay = open_gif(index)
        next_frame = time.monotonic() + delay
        next_asset = time.monotonic() + 12
        print("GIF changed:", FILES[index], "free RAM:", gc.mem_free())
    elif now >= next_frame:
        started = time.monotonic()
        delay = max(0.04, gif.next_frame())
        elapsed = (time.monotonic() - started) * 1000
        max_decode_ms = max(max_decode_ms, elapsed)
        frames += 1
        next_frame = time.monotonic() + delay
    if now >= next_report:
        print("GIF frames/5s:", frames, "max decode ms:", round(max_decode_ms, 1),
              "free RAM:", gc.mem_free())
        frames = 0
        max_decode_ms = 0.0
        next_report = now + 5
    time.sleep(0.005)
