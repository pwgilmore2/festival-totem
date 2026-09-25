"""Festival Totem MatrixPortal S3 app. Copy the staged build to CIRCUITPY.

This is the first integrated hardware candidate; read MATRIXPORTAL_DEPLOYMENT.md.
"""

import gc
import os
import time

import socketpool
import wifi

from embedded_icon_library import EMBEDDED_ICON_LIBRARY
from matrixportal_bitmap_buffer_probe import run as probe_bitmap_buffer
from matrixportal_backend import MatrixPortalDisplayBackend
from matrixportal_effects import EFFECTS
from matrixportal_library import MatrixPortalMediaAdapter
from matrixportal_server import MatrixPortalControlServer
from overlay_engine import OverlayRenderer
from runtime_metrics import RuntimeMetrics
from totem_runtime import TotemRuntime


FPS = 30  # Target; physical display/HTTP timings decide the delivered rate.
PANEL_BRIGHTNESS_CAP = 0.35  # Temporary physical LED limit; phone slider can dim further.
REPORT_SECONDS = 5
BITMAP_BUFFER_PROBE = True  # One-shot startup measurement; no live renderer changes.
WIFI_SSID = "Festival-Totem"
WIFI_PASSWORD = ""  # Set a private WPA password of at least eight characters.


def launch():
    # On-device profile: native bitmaptools.blit reduced mirrored GIF copy
    # from ~508 ms to ~4 ms, at bit depth 1. Keep pixel-layer writes logical
    # RGB565 through the backend's swapped-storage adapter.
    backend = MatrixPortalDisplayBackend(bit_depth=1, doublebuffer=False,
                                          swapped_storage=True)
    backend.set_brightness(PANEL_BRIGHTNESS_CAP)
    applied_brightness = PANEL_BRIGHTNESS_CAP
    if BITMAP_BUFFER_PROBE:
        probe_bitmap_buffer(backend.bitmap)
    media = MatrixPortalMediaAdapter()
    if not len(media):
        raise RuntimeError("Add prepared GIFs to assets/images and rebuild the manifest")
    icons = EMBEDDED_ICON_LIBRARY
    runtime = TotemRuntime(64, 32, backend.displays, media, icons,
                           OverlayRenderer(64, 32, icons), EFFECTS, mirrored=True)
    # The default Dimmed background touches all 4096 panel pixels in Python
    # on every icon frame (measured 0.58-1.7 seconds per render). Keep the GIF
    # visible beneath overlays on this board until dimming can run natively.
    runtime.set_overlay_background("None")

    if len(WIFI_PASSWORD) < 8:
        raise RuntimeError("Set WIFI_PASSWORD in code.py to at least eight characters")
    wifi.radio.start_ap(ssid=WIFI_SSID, password=WIFI_PASSWORD)
    address = wifi.radio.ipv4_address_ap
    server = MatrixPortalControlServer(socketpool.SocketPool(wifi.radio), address)
    print("Controller:", server.start())

    metrics = RuntimeMetrics(REPORT_SECONDS)
    diagnostics = None
    if "totem_diagnostics.flag" in os.listdir("/"):
        from matrixportal_diagnostics import BoardDiagnostics
        diagnostics = BoardDiagnostics(runtime, media, backend)

    if diagnostics is None:
        record = metrics.add_timing
    else:
        def record(label, elapsed):
            metrics.add_timing(label, elapsed)
            diagnostics.profile(label, elapsed)

    runtime.profile_render = record
    runtime.layer_engine.profile = record
    runtime.chaos_engine.profile = record
    last_frame = time.monotonic()
    next_frame = last_frame
    next_state = last_frame
    frame_number = 0
    try:
        server.update_state(runtime.controller_state())
        while True:
            loop_started = time.monotonic()
            if diagnostics is not None:
                diagnostics.tick(loop_started)
            started = loop_started
            server.poll()
            record("http", time.monotonic() - started)

            for command in server.get_commands():
                started = time.monotonic()
                runtime.handle_command(command)
                record("command", time.monotonic() - started)

            started = time.monotonic()
            media.advance(started, max_decodes=1)
            record("decode/check", time.monotonic() - started)

            now = time.monotonic()
            if now >= next_frame:
                record("frame/interval", now - last_frame)
                record("frame/lateness", max(0.0, now - next_frame))
                dt = min(.25, now - last_frame)
                last_frame = now
                started = time.monotonic()
                runtime.update(dt)
                record("update", time.monotonic() - started)
                started = time.monotonic()
                if diagnostics is not None and not diagnostics.done:
                    try:
                        runtime.render(frame_number)
                    except Exception as exc:
                        diagnostics.skip_current(exc)
                        continue
                else:
                    runtime.render(frame_number)
                record("render", time.monotonic() - started)
                if runtime.mirrored:
                    requested_brightness = runtime.controllers["front"].brightness
                else:
                    # One RGBMatrix brightness setting controls both faces.
                    requested_brightness = min(controller.brightness
                                               for controller in runtime.controllers.values())
                physical_brightness = PANEL_BRIGHTNESS_CAP * requested_brightness
                if physical_brightness != applied_brightness:
                    backend.set_brightness(physical_brightness)
                    applied_brightness = physical_brightness
                started = time.monotonic()
                backend.present()
                record("present", time.monotonic() - started)
                metrics.frame()
                if diagnostics is not None:
                    diagnostics.frame(time.monotonic())
                frame_number += 1
                # Frame period starts at the scheduled frame, not after its
                # render/present work. Otherwise 50 ms + ~14 ms yields ~15 FPS.
                next_frame = now + 1 / FPS

            now = time.monotonic()
            if now >= next_state:
                started = now
                server.update_state(runtime.controller_state())
                record("state", time.monotonic() - started)
                next_state = time.monotonic() + .5
            metrics.loop()
            record("loop", time.monotonic() - loop_started)
            if metrics.due():
                # A forced collection measured ~120 ms every five seconds,
                # visibly interrupting otherwise steady GIF playback.
                if gc.mem_free() < 300000:
                    gc_started = time.monotonic()
                    gc.collect()
                    record("gc", time.monotonic() - gc_started)
                report = metrics.take_report(free_ram=gc.mem_free())
                report["chaos_mode"] = runtime.chaos_engine.mode
                print("Performance:", report)
    finally:
        server.stop()
        media.close()
        backend.deinit()


launch()
