import time

import pygame

from desktop_media import DesktopMediaAdapter
from effects import EFFECTS
from icon_assets import ICON_LIBRARY
from overlay_engine import OverlayRenderer
from runtime_io import VirtualDisplayBackend
from secure_phone_server import PhoneControlServer
from totem_runtime import SIDES, TotemRuntime


W, H, SCALE, GAP, UI_HEIGHT = 64, 32, 8, 24, 185
PANEL_W, PANEL_H = W * SCALE, H * SCALE
PHONE_STATE_INTERVAL = 0.10


pygame.init()
screen = pygame.display.set_mode((PANEL_W * 2 + GAP, PANEL_H + UI_HEIGHT))
pygame.display.set_caption("Festival Totem Simulator")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)

media = DesktopMediaAdapter("assets/images", W, H)
display_backend = VirtualDisplayBackend(W, H)
overlay_renderer = OverlayRenderer(W, H, ICON_LIBRARY)
runtime = TotemRuntime(
    W,
    H,
    display_backend.displays,
    media,
    ICON_LIBRARY,
    overlay_renderer,
    EFFECTS,
)

server = PhoneControlServer(8765)
server.set_thumbnail_provider(media.thumbnail)
phone_url = server.start()


def update_phone():
    server.update_state(runtime.controller_state())


def draw_panel(side, x):
    display = runtime.displays[side]
    brightness = runtime.controllers[side].brightness
    for y in range(H):
        for px in range(W):
            color = display.get_pixel(px, y)
            pygame.draw.rect(
                screen,
                (
                    int(color[0] * brightness),
                    int(color[1] * brightness),
                    int(color[2] * brightness),
                ),
                (x + px * SCALE, y * SCALE, SCALE - 1, SCALE - 1),
            )


def draw_ui():
    front = runtime.phone_panel("front")
    back = runtime.phone_panel("back")
    audio = runtime.audio

    screen.blit(
        font.render(
            "FRONT: %s | %s" % (front["effect"], front["image_name"] or "-"),
            True,
            (220, 220, 220),
        ),
        (10, PANEL_H + 10),
    )
    screen.blit(
        font.render(
            "BACK: %s | %s" % (back["effect"], back["image_name"] or "-"),
            True,
            (220, 220, 220),
        ),
        (10, PANEL_H + 36),
    )
    screen.blit(
        font.render(
            "Target: %s   %s" % (runtime.active_target.upper(), phone_url),
            True,
            (190, 190, 190),
        ),
        (10, PANEL_H + 62),
    )
    screen.blit(
        font.render(
            "Audio V:%.2f B:%.2f M:%.2f H:%.2f Beat:%s"
            % (
                audio["volume"],
                audio["bass"],
                audio["mids"],
                audio["highs"],
                "YES" if audio["beat"] else "-",
            ),
            True,
            (170, 205, 255),
        ),
        (10, PANEL_H + 88),
    )
    screen.blit(
        font.render(
            "Scene: %s  Beat Sync: %s"
            % (
                runtime.current_scene,
                "ON" if front["slideshow"]["beat_sync"] else "OFF",
            ),
            True,
            (185, 185, 220),
        ),
        (10, PANEL_H + 114),
    )


def handle_key(key):
    if key == pygame.K_ESCAPE:
        return False
    if key == pygame.K_f:
        runtime.set_target("front")
    elif key == pygame.K_b:
        runtime.set_target("back")
    elif key == pygame.K_m:
        runtime.set_target("both")
    elif key == pygame.K_SPACE:
        runtime.toggle_pause()
    return True


update_phone()
running = True
frame_number = 0
last_phone_update = time.monotonic()

while running:
    dt = clock.tick(60) / 1000.0
    frame_number += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            running = handle_key(event.key)

    for data in server.get_commands():
        runtime.handle_command(data)

    runtime.step(dt, frame_number)

    screen.fill((15, 15, 18))
    draw_panel("front", 0)
    draw_panel("back", PANEL_W + GAP)
    draw_ui()

    now = time.monotonic()
    if now - last_phone_update >= PHONE_STATE_INTERVAL:
        update_phone()
        last_phone_update = now

    pygame.display.flip()

server.stop()
pygame.quit()
