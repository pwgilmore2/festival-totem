"""Two-panel GIF and phone Wi-Fi bring-up, using only built-in CircuitPython.

Copy as CIRCUITPY/code.py alongside the two test GIFs in CIRCUITPY/media/.
This standalone controller tests the network path before the full app runtime.
"""

import board
import displayio
import framebufferio
import gc
import gifio
import rgbmatrix
import socketpool
import time
import wifi


SSID = "Festival-Totem-Test"
PASSWORD = "totemtest2026"  # Temporary bench-test password; change for field use.
FILES = ("/media/test_orbit.gif", "/media/test_wave.gif")
PAGE = ("<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
        "<style>body{font:22px system-ui;background:#10121b;color:white;margin:28px}"
        "a{display:block;padding:23px;margin:18px 0;background:#513aaa;color:white;"
        "border-radius:16px;text-decoration:none;text-align:center}</style>"
        "<h2>Festival Totem</h2><p>Both screens mirror the selected animation.</p>"
        "<a href='/gif/0'>Orbit</a><a href='/gif/1'>Wave</a>")


displayio.release_displays()
pins = dict(board.MTX_COMMON)
r1, g1, b1, r2, g2, b2 = pins["rgb_pins"]
pins["rgb_pins"] = (r1, b1, g1, r2, b2, g2)
matrix = rgbmatrix.RGBMatrix(width=128, height=32, bit_depth=1,
                             addr_pins=board.MTX_ADDRESS[:4], tile=1, **pins)
display = framebufferio.FramebufferDisplay(matrix)
group = displayio.Group()
display.root_group = group
shader = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB565_SWAPPED)


def start_animation(index):
    current = gifio.OnDiskGif(FILES[index])
    delay = max(0.04, current.next_frame())
    group.append(displayio.TileGrid(current.bitmap, pixel_shader=shader, x=0))
    group.append(displayio.TileGrid(current.bitmap, pixel_shader=shader, x=64))
    return current, time.monotonic() + delay


def send_page(client):
    body = PAGE.encode("utf-8")
    response = ("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                "Content-Length: %d\r\nConnection: close\r\n\r\n" % len(body)).encode() + body
    while response:
        count = client.send(response)
        if not count:
            break
        response = response[count:]


print("Starting totem test Wi-Fi:", SSID)
wifi.radio.start_ap(ssid=SSID, password=PASSWORD)
address = str(wifi.radio.ipv4_address_ap)
pool = socketpool.SocketPool(wifi.radio)
server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
server.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
server.bind((address, 5000))
server.listen(2)
server.settimeout(0)
print("Phone address: http://" + address + ":5000")

index = 0
gif, next_frame = start_animation(index)
last_report = time.monotonic()
frames = 0
worst_decode_ms = 0.0
while True:
    try:
        client, _ = server.accept()
    except OSError:
        client = None
    if client is not None:
        try:
            client.settimeout(1)
            request_buffer = bytearray(512)
            received = client.recv_into(request_buffer)
            request = bytes(request_buffer[:received])
            path = request.split(b" ", 2)[1] if b" " in request else b"/"
            if path in (b"/gif/0", b"/gif/1"):
                selected = int(path[-1:])
                if selected != index:
                    group.pop()
                    group.pop()
                    gif.deinit()
                    gc.collect()
                    index = selected
                    gif, next_frame = start_animation(index)
                    print("Phone selected:", FILES[index])
            send_page(client)
        except (OSError, IndexError, ValueError) as exc:
            print("HTTP request skipped:", exc)
        finally:
            client.close()
    now = time.monotonic()
    if now >= next_frame:
        started = now
        delay = max(0.04, gif.next_frame())
        worst_decode_ms = max(worst_decode_ms, (time.monotonic() - started) * 1000)
        frames += 1
        next_frame = time.monotonic() + delay
    if now - last_report >= 5:
        print("frames/5s:", frames, "max decode ms:", round(worst_decode_ms, 1),
              "free RAM:", gc.mem_free())
        frames = 0
        worst_decode_ms = 0.0
        last_report = now
    time.sleep(0.005)
