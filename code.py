"""Festival Totem MatrixPortal S3 app. Copy the staged build to CIRCUITPY.

This is the first integrated hardware candidate; read MATRIXPORTAL_DEPLOYMENT.md.
"""

import gc
import time

import socketpool
import wifi

from embedded_icon_library import EMBEDDED_ICON_LIBRARY
from matrixportal_backend import MatrixPortalDisplayBackend
from matrixportal_effects import EFFECTS
from matrixportal_library import MatrixPortalMediaAdapter
from matrixportal_server import MatrixPortalControlServer
from overlay_engine import OverlayRenderer
from runtime_metrics import RuntimeMetrics
from totem_runtime import TotemRuntime


FPS = 20  # Conservative starting point; record physical timings before tuning.
REPORT_SECONDS = 5
WIFI_SSID = "Festival-Totem"
WIFI_PASSWORD = ""  # Set a private WPA password of at least eight characters.


def launch():
    # On-device profile: native bitmaptools.blit reduced mirrored GIF copy
    # from ~508 ms to ~4 ms, at bit depth 1. Keep pixel-layer writes logical
    # RGB565 through the backend's swapped-storage adapter.
    backend = MatrixPortalDisplayBackend(bit_depth=1, doublebuffer=False,
                                          swapped_storage=True)
    media = MatrixPortalMediaAdapter()
    if not len(media):
        raise RuntimeError("Add prepared GIFs to assets/images and rebuild the manifest")
    icons = EMBEDDED_ICON_LIBRARY
    runtime = TotemRuntime(64, 32, backend.displays, media, icons,
                           OverlayRenderer(64, 32, icons), EFFECTS)

    if len(WIFI_PASSWORD) < 8:
        raise RuntimeError("Set WIFI_PASSWORD in code.py to at least eight characters")
    wifi.radio.start_ap(ssid=WIFI_SSID, password=WIFI_PASSWORD)
    address = wifi.radio.ipv4_address_ap
    server = MatrixPortalControlServer(socketpool.SocketPool(wifi.radio), address)
    print("Controller:", server.start())

    metrics = RuntimeMetrics(REPORT_SECONDS)
    last_frame = time.monotonic()
    next_frame = last_frame
    next_state = last_frame
    frame_number = 0
    try:
        server.update_state(runtime.controller_state())
        while True:
            loop_started = time.monotonic()
            started = loop_started
            server.poll()
            metrics.add_timing("http", time.monotonic() - started)

            for command in server.get_commands():
                started = time.monotonic()
                runtime.handle_command(command)
                metrics.add_timing("command", time.monotonic() - started)

            started = time.monotonic()
            media.advance(started, max_decodes=1)
            metrics.add_timing("decode/check", time.monotonic() - started)

            now = time.monotonic()
            if now >= next_frame:
                dt = min(.25, now - last_frame)
                last_frame = now
                started = time.monotonic()
                runtime.update(dt)
                metrics.add_timing("update", time.monotonic() - started)
                started = time.monotonic()
                runtime.render(frame_number)
                metrics.add_timing("render", time.monotonic() - started)
                started = time.monotonic()
                backend.present()
                metrics.add_timing("present", time.monotonic() - started)
                metrics.frame()
                frame_number += 1
                next_frame = time.monotonic() + 1 / FPS

            now = time.monotonic()
            if now >= next_state:
                started = now
                server.update_state(runtime.controller_state())
                metrics.add_timing("state", time.monotonic() - started)
                next_state = time.monotonic() + .5
            metrics.loop()
            metrics.add_timing("loop", time.monotonic() - loop_started)
            if metrics.due():
                print("Performance:", metrics.take_report(free_ram=gc.mem_free()))
                gc.collect()
    finally:
        server.stop()
        media.close()
        backend.deinit()


launch()
