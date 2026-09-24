"""First-light test for two chained 64x32 HUB75 panels on MatrixPortal S3.

Copy this file to CIRCUITPY/code.py along with matrixportal_backend.py.
The panel nearest the controller should show red, green, blue; the second
should show blue, red, green. Colors are deliberately dim for bench testing.
"""

import time

from matrixportal_backend import MatrixPortalDisplayBackend


print("Starting two-panel first-light test")
backend = MatrixPortalDisplayBackend(width=64, height=32, bit_depth=3)
backend.set_brightness(0.15)

while True:
    for front, back, name in (
        ((48, 0, 0), (0, 0, 48), "front red / back blue"),
        ((0, 48, 0), (48, 0, 0), "front green / back red"),
        ((0, 0, 48), (0, 48, 0), "front blue / back green"),
    ):
        backend.get("front").fill(front)
        backend.get("back").fill(back)
        backend.present()
        print(name)
        time.sleep(2)
