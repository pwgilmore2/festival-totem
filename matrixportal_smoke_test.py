"""First physical-hardware smoke test for the Festival Totem MatrixPortal S3.

Copy the hardware modules plus a generated ``manifest.json`` and ``media/``
folder to CIRCUITPY, rename this file to ``code.py`` temporarily, and watch the
serial console.

The loop is intentionally cooperative/non-blocking: GIF decode, render/present,
state reporting, and future HTTP/audio work each get independent timers. No
``sleep()`` is used for frame pacing.
"""

import gc
import time

from matrixportal_library import MatrixPortalAssetLibrary, MatrixPortalMediaDeck
from runtime_io import HardwareDisplayBackend


WIDTH = 64
HEIGHT = 32
BIT_DEPTH = 4
TARGET_FPS = 30
REPORT_SECONDS = 5.0

# Change BACK_ROTATION to 180 if the rear-facing physical panel is mounted
# upside-down relative to the front panel.
FRONT_ROTATION = 0
BACK_ROTATION = 0


def memory_free():
    value = getattr(gc, "mem_free", None)
    return value() if value else -1


def main():
    print("Festival Totem MatrixPortal S3 smoke test")
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

    mapping_until = time.monotonic() + 2.0
    while time.monotonic() < mapping_until:
        # Intentionally no sleep: this mirrors the final cooperative loop where
        # Wi-Fi/server/audio polling will have work to do between display frames.
        pass

    library = MatrixPortalAssetLibrary("/manifest.json")
    print("Prepared assets:", len(library))
    if not len(library):
        raise RuntimeError("manifest.json contains no prepared assets")

    media = MatrixPortalMediaDeck(library)
    media.select("front", 0)
    media.select("back", 1 if len(library) > 1 else 0)
    print("Free RAM after two GIF decoders:", memory_free())

    frame_interval = 1.0 / TARGET_FPS
    now = time.monotonic()
    next_present_at = now
    next_report_at = now + REPORT_SECONDS
    frames = 0
    report_started = now

    try:
        while True:
            now = time.monotonic()

            # Independent front/back file pointers. At most one synchronous
            # gifio decode is allowed per loop iteration to avoid a double-I/O
            # spike when both GIF deadlines line up.
            media.advance(now)

            # Rendering/presenting has its own cadence and never blocks waiting
            # for the next deadline. If work ran late, drop timing debt rather
            # than trying to catch up with multiple presents.
            if now >= next_present_at:
                media.render(displays)
                backend.present()
                frames += 1
                next_present_at = now + frame_interval

            if now >= next_report_at:
                elapsed = max(0.001, now - report_started)
                front_player = media.players.players["front"]
                back_player = media.players.players["back"]
                print(
                    "FPS:", round(frames / elapsed, 1),
                    "free RAM:", memory_free(),
                    "GIF frames F/B:",
                    front_player.frames_advanced,
                    back_player.frames_advanced,
                )
                frames = 0
                report_started = now
                next_report_at = now + REPORT_SECONDS
                gc.collect()
    finally:
        media.close()
        backend.deinit()


main()
