"""Validate TotemRuntime's per-pixel backend using proven displayio canvas.

Copy to CIRCUITPY/code.py with the accompanying matrixportal_backend.py.
"""

import gc
import time

from matrixportal_backend import MatrixPortalDisplayBackend

print("BITMAP BACKEND: free RAM before", gc.mem_free())
backend = MatrixPortalDisplayBackend(width=64, height=32)
print("BITMAP BACKEND: initialized, free RAM", gc.mem_free())
front = backend.get("front")
back = backend.get("back")
for side in (front, back):
    side.clear()
for y in range(4, 12):
    for x in range(4, 12):
        front.set_pixel(x, y, (255, 0, 0))
        back.set_pixel(x, y, (0, 0, 255))
backend.present()
print("BITMAP BACKEND: red first, blue second")
while True:
    time.sleep(1)
