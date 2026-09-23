"""Physical-hardware performance smoke test for the Festival Totem S3.

Copy the hardware modules plus a generated ``manifest.json`` and ``media/``
folder to CIRCUITPY, rename this file to ``code.py`` temporarily, and watch the
serial console.

The loop is cooperative/non-blocking: GIF decode and display present have their
own deadlines and no ``sleep()`` is used for frame pacing. Measurements here are
intentionally device-side; desktop timings are not treated as S3 predictions.
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


def human_bytes(value):
    value = int(value or 0)
    if value < 1024:
        return "%d B" % value
    if value < 1024 * 1024:
        return "%0.1f KiB" % (value / 1024.0)
    return "%0.2f MiB" % (value / (1024.0 * 1024.0))


class TimingStats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.samples = 0
        self.total_ms = 0.0
        self.max_ms = 0.0

    def add(self, seconds):
        ms = max(0.0, float(seconds) * 1000.0)
        self.samples += 1
        self.total_ms += ms
        if ms > self.max_ms:
            self.max_ms = ms

    def average_ms(self):
        return self.total_ms / self.samples if self.samples else 0.0


def main():
    print("Festival Totem MatrixPortal S3 performance test")
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
        pass

    library = MatrixPortalAssetLibrary("/manifest.json")
    print("Prepared assets:", len(library))
    print("Baked media:", library.baked_media)
    if library.media_bytes():
        print("GIF media on flash:", human_bytes(library.media_bytes()))
    if library.storage_bytes():
        print("Prepared deployment payload:", human_bytes(library.storage_bytes()))
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
    loop_iterations = 0
    report_started = now
    decode_timing = TimingStats()
    present_timing = TimingStats()
    loop_timing = TimingStats()

    try:
        while True:
            loop_started = time.monotonic()
            now = loop_started

            # Independent front/back file pointers. At most one synchronous
            # gifio decode is allowed per loop iteration to avoid double-I/O
            # spikes when both GIF deadlines line up.
            decode_started = time.monotonic()
            decoded = media.advance(now)
            decode_elapsed = time.monotonic() - decode_started
            if decoded:
                decode_timing.add(decode_elapsed)

            # Rendering/presenting has its own cadence. If work ran late, timing
            # debt is dropped rather than trying to burst several frames.
            now = time.monotonic()
            if now >= next_present_at:
                present_started = now
                media.render(displays)
                backend.present()
                present_timing.add(time.monotonic() - present_started)
                frames += 1
                next_present_at = now + frame_interval

            loop_iterations += 1
            loop_timing.add(time.monotonic() - loop_started)

            now = time.monotonic()
            if now >= next_report_at:
                elapsed = max(0.001, now - report_started)
                front_player = media.players.players["front"]
                back_player = media.players.players["back"]
                print(
                    "FPS", round(frames / elapsed, 1),
                    "loops/s", round(loop_iterations / elapsed, 0),
                    "RAM", memory_free(),
                    "decode avg/max ms", round(decode_timing.average_ms(), 2),
                    "/", round(decode_timing.max_ms, 2),
                    "present avg/max ms", round(present_timing.average_ms(), 2),
                    "/", round(present_timing.max_ms, 2),
                    "loop max ms", round(loop_timing.max_ms, 2),
                    "GIF frames F/B", front_player.frames_advanced,
                    "/", back_player.frames_advanced,
                )
                frames = 0
                loop_iterations = 0
                report_started = now
                next_report_at = now + REPORT_SECONDS
                decode_timing.reset()
                present_timing.reset()
                loop_timing.reset()
                gc.collect()
    finally:
        media.close()
        backend.deinit()


main()
