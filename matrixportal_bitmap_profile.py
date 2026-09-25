"""Small, dependency-free hardware profile of prepared GIFs on the Bitmap backend.

Stage with tools/stage_bitmap_profile.py. This intentionally excludes HTTP,
overlays and transitions so a physical slowdown can be attributed to the GIF
decoder, RGB565 pixel copy, or display refresh.
"""

import gc
import json
import time

import gifio

from matrixportal_backend import MatrixPortalDisplayBackend


REPORT_INTERVAL = 5.0
SWITCH_INTERVAL = 12.0
MIN_FRAME_DELAY = 0.04


def open_gif(path):
    player = gifio.OnDiskGif(path)
    delay = max(MIN_FRAME_DELAY, float(player.next_frame()))
    return player, time.monotonic() + delay


def run():
    with open("/manifest.json", "r") as handle:
        assets = json.load(handle)["assets"]
    paths = [asset["file"] for asset in assets]
    if not paths:
        raise RuntimeError("Profile build has no GIFs")

    print("Bitmap profile: starting display", gc.mem_free())
    backend = MatrixPortalDisplayBackend(bit_depth=1, doublebuffer=False,
                                          swapped_storage=True)
    front, back = backend.displays["front"], backend.displays["back"]
    backend.set_brightness(0.25)
    print("Bitmap profile: display ready", gc.mem_free())
    index = 0
    player, next_frame = open_gif(paths[index])
    next_switch = time.monotonic() + SWITCH_INTERVAL
    print("GIF", index, paths[index], "RAM", gc.mem_free())
    reports_at = time.monotonic() + REPORT_INTERVAL
    decoded = rendered = 0
    max_decode = max_copy = max_present = 0.0

    try:
        while True:
            now = time.monotonic()
            if len(paths) > 1 and now >= next_switch:
                player.deinit()
                gc.collect()
                index = (index + 1) % len(paths)
                player, next_frame = open_gif(paths[index])
                next_switch = time.monotonic() + SWITCH_INTERVAL
                print("GIF", index, paths[index], "RAM", gc.mem_free())

            if now >= next_frame:
                started = time.monotonic()
                delay = max(MIN_FRAME_DELAY, float(player.next_frame()))
                max_decode = max(max_decode, time.monotonic() - started)
                decoded += 1
                next_frame = time.monotonic() + delay

                started = time.monotonic()
                front.blit_rgb565_swapped(player.bitmap)
                back.blit_rgb565_swapped(player.bitmap)
                max_copy = max(max_copy, time.monotonic() - started)
                started = time.monotonic()
                backend.present()
                max_present = max(max_present, time.monotonic() - started)
                rendered += 1

            now = time.monotonic()
            if now >= reports_at:
                print("PROFILE fps", rendered / REPORT_INTERVAL,
                      "decoded", decoded, "RAM", gc.mem_free(),
                      "max decode/copy/present ms",
                      round(max_decode * 1000, 1),
                      round(max_copy * 1000, 1),
                      round(max_present * 1000, 1),
                      "GIF", index)
                decoded = rendered = 0
                max_decode = max_copy = max_present = 0.0
                gc.collect()
                reports_at = now + REPORT_INTERVAL
            time.sleep(0.005)
    finally:
        player.deinit()
        backend.deinit()


run()
