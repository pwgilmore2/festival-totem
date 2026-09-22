"""First physical-hardware smoke test for the festival totem.

Copy this repository's hardware modules plus a generated ``manifest.json`` and
``media/`` folder to CIRCUITPY, rename this file to ``code.py`` temporarily, and
watch the serial console.

This intentionally does not start Wi-Fi or the phone controller. It answers the
first two hardware questions in isolation:
1. Do both chained logical 64x32 panels map correctly?
2. Can two independent gifio streams run at a steady cadence within RAM?
"""

import gc
import time

from matrixportal_library import MatrixPortalAssetLibrary, MatrixPortalMediaDeck
from runtime_io import HardwareDisplayBackend


WIDTH = 64
HEIGHT = 32
BIT_DEPTH = 2
TARGET_FPS = 24

# Change BACK_ROTATION to 180 if the rear-facing physical panel is mounted
# upside-down relative to the front panel.
FRONT_ROTATION = 0
BACK_ROTATION = 0


def memory_free():
    value = getattr(gc, "mem_free", None)
    return value() if value else -1


def main():
    print("Festival Totem MatrixPortal smoke test")
    print("Free RAM before display:", memory_free())

    backend = HardwareDisplayBackend(
        WIDTH,
        HEIGHT,
        bit_depth=BIT_DEPTH,
        front_rotation=FRONT_ROTATION,
        back_rotation=BACK_ROTATION,
        doublebuffer=True,
    )
    displays = backend.displays
    print("Free RAM after display:", memory_free())

    # Mapping test: front should be red, back should be blue.
    displays["front"].fill((255, 0, 0))
    displays["back"].fill((0, 0, 255))
    backend.present()
    print("Panel mapping test: FRONT=red BACK=blue")
    time.sleep(2.0)

    library = MatrixPortalAssetLibrary("/manifest.json")
    print("Prepared assets:", len(library))
    if not len(library):
        raise RuntimeError("manifest.json contains no prepared assets")

    media = MatrixPortalMediaDeck(library)
    media.select("front", 0)
    media.select("back", 1 if len(library) > 1 else 0)
    print("Free RAM after two GIF decoders:", memory_free())

    frame_interval = 1.0 / TARGET_FPS
    next_frame = time.monotonic()
    frames = 0
    report_started = next_frame

    try:
        while True:
            now = time.monotonic()
            remaining = next_frame - now
            if remaining > 0:
                time.sleep(remaining)
                now = time.monotonic()

            # Schedule from the current time if a frame ran late rather than
            # spinning to catch up and starving the GIF decoder or Wi-Fi later.
            next_frame = now + frame_interval

            media.advance(now)
            media.render(displays)
            backend.present()
            frames += 1

            elapsed = now - report_started
            if elapsed >= 5.0:
                print(
                    "FPS:",
                    round(frames / elapsed, 1),
                    "free RAM:",
                    memory_free(),
                )
                frames = 0
                report_started = now
                gc.collect()
    finally:
        media.close()
        backend.deinit()


main()
