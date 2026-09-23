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
from runtime_metrics import RuntimeMetrics


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


def timing(report, name):
    item = report.get("timings", {}).get(name, {})
    return item.get("avg_ms", 0.0), item.get("max_ms", 0.0)


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
    metrics = RuntimeMetrics(REPORT_SECONDS)

    try:
        while True:
            loop_started = time.monotonic()
            now = loop_started

            # Independent front/back file pointers. At most one synchronous
            # gifio decode is allowed per loop iteration to avoid double-I/O
            # spikes when both GIF deadlines line up.
            decode_started = time.monotonic()
            decoded = media.advance(now)
            if decoded:
                metrics.add_timing("decode", time.monotonic() - decode_started)

            # Rendering/presenting has its own cadence. If work ran late, timing
            # debt is dropped rather than trying to burst several frames.
            now = time.monotonic()
            if now >= next_present_at:
                present_started = now
                media.render(displays)
                backend.present()
                metrics.add_timing("present", time.monotonic() - present_started)
                metrics.frame()
                next_present_at = now + frame_interval

            metrics.loop()
            metrics.add_timing("loop", time.monotonic() - loop_started)

            now = time.monotonic()
            if metrics.due(now):
                report = metrics.take_report(now, free_ram=memory_free())
                decode_avg, decode_max = timing(report, "decode")
                present_avg, present_max = timing(report, "present")
                _, loop_max = timing(report, "loop")
                front_player = media.players.players["front"]
                back_player = media.players.players["back"]
                print(
                    "FPS", round(report["fps"], 1),
                    "loops/s", round(report["loops_per_second"], 0),
                    "RAM", report["free_ram"],
                    "decode avg/max ms", round(decode_avg, 2), "/", round(decode_max, 2),
                    "present avg/max ms", round(present_avg, 2), "/", round(present_max, 2),
                    "loop max ms", round(loop_max, 2),
                    "GIF frames F/B", front_player.frames_advanced, "/", back_player.frames_advanced,
                )
                gc.collect()
    finally:
        media.close()
        backend.deinit()


main()
