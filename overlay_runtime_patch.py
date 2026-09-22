import math
import random

import controller_state_ui
import performance_extras
from text_engine import parse_color, hsv_color, clamp01

OVERLAY_ICONS = [
    "Heart", "Mushroom", "Wakaan Sigil", "Sprout", "Rune 2H", "Eye",
    "Skull", "Alien", "Smiley", "Crystal", "Moth", "Orb",
]

# Compact hand-drawn pixel sprites. These are original simplified designs meant
# to read cleanly on a 64x32 LED matrix rather than imitate source artwork.
SPRITES = {
    "Heart": [
        "01100110","11111111","11111111","11111111","01111110","00111100","00011000",
    ],
    "Mushroom": [
        "00111100","01111110","11111111","11011011","01111110","00011000","00111100","00111100",
    ],
    "Wakaan Sigil": [
        "10000001","10011001","10111101","11100111","11100111","10111101","10011001","10000001",
    ],
    "Sprout": [
        "00100100","01110110","00111100","00011000","00011000","00011000","00111100","01111110",
    ],
    "Rune 2H": [
        "00011000","00111100","01111110","00111100","00011000","00011000","01111110","00111100","00011000","00011000","00100100",
    ],
    "Eye": [
        "00011000","01111110","11100111","11011011","11011011","11100111","01111110","00011000",
    ],
    "Skull": [
        "00111100","01111110","11111111","11011011","11111111","01111110","00100100","00111100",
    ],
    "Alien": [
        "00111100","01111110","11111111","11011011","10000001","01100110","00111100",
    ],
    "Smiley": [
        "00111100","01111110","11011011","11111111","10111101","11000011","01111110","00111100",
    ],
    "Crystal": [
        "00011000","00111100","01111110","11111111","01111110","00111100","00011000",
    ],
    "Moth": [
        "10000001","11011011","11111111","01111110","00111100","01111110","11111111","10000001",
    ],
    "Orb": [
        "00111100","01111110","11100111","11011011","11011011","11100111","01111110","00111100",
    ],
}

_overlay = {
    "front": {"type": "Text", "icon": "Heart", "motion": "Static"},
    "back": {"type": "Text", "icon": "Heart", "motion": "Static"},
}


def _side(seed):
    return "back" if int(seed or 0) >= 1000 else "front"


def _put(display, x, y, color):
    if 0 <= x < display.width and 0 <= y < display.height:
        display.set_pixel(x, y, color)


def _sprite_dimensions(name):
    rows = SPRITES.get(name, SPRITES["Heart"])
    return max(len(r) for r in rows), len(rows)


def _draw_sprite(display, name, cx, cy, scale, color, glow=False, glitch=False, seed=0):
    rows = SPRITES.get(name, SPRITES["Heart"])
    w, h = _sprite_dimensions(name)
    x0 = int(round(cx - (w * scale) / 2))
    y0 = int(round(cy - (h * scale) / 2))
    rng = random.Random(seed)

    points = []
    for yy, row in enumerate(rows):
        for xx, bit in enumerate(row):
            if bit != "1":
                continue
            px = x0 + xx * scale
            py = y0 + yy * scale
            if glitch and rng.random() < .10:
                px += rng.choice((-2, -1, 1, 2))
            for sy in range(scale):
                for sx in range(scale):
                    points.append((px + sx, py + sy))

    if glow:
        g = tuple(max(12, int(c * .28)) for c in color)
        for px, py in points:
            for ox, oy in ((-1,0),(1,0),(0,-1),(0,1)):
                _put(display, px + ox, py + oy, g)
    for px, py in points:
        _put(display, px, py, color)


def _render_icon(renderer, display, settings, t, signals=None, seed=0, clear_background=True):
    signals = signals or {}
    side = _side(seed)
    st = _overlay[side]
    if clear_background:
        display.clear()

    name = st.get("icon", "Heart")
    scale = max(1, min(3, int(settings.get("scale", 2))))
    w, h = _sprite_dimensions(name)
    while scale > 1 and (w * scale > renderer.width - 6 or h * scale > renderer.height - 6):
        scale -= 1

    bass = clamp01(signals.get("bass", 0.0))
    mids = clamp01(signals.get("mids", 0.0))
    highs = clamp01(signals.get("highs", 0.0))
    beat = bool(signals.get("beat", False))
    audio_mode = settings.get("audio_reactivity", "Off")
    speed = max(1.0, min(40.0, float(settings.get("speed", 22.0))))

    cx = renderer.width / 2
    cy = renderer.height / 2
    motion = st.get("motion", "Static")
    rate = speed / 22.0
    if motion == "Float":
        cx += math.sin(t * 1.35 * rate) * 3.0
        cy += math.cos(t * 1.05 * rate) * 2.0
    elif motion == "Bounce":
        cy += abs(math.sin(t * 2.5 * rate)) * -4.0 + 2.0

    if settings.get("wave"):
        cy += math.sin(t * 3.8 * rate) * 2.0

    if audio_mode == "Subtle":
        cy += math.sin(t * 5.0) * bass * 1.4
        if beat:
            cy -= 1
    elif audio_mode == "Reactive":
        cy += math.sin(t * 6.0) * bass * 3.0
        cx += math.sin(t * 3.1) * mids * 2.0
        if beat:
            cy -= 2

    pulse = 1.0
    if settings.get("beat_pulse") and beat:
        pulse = 1.25
    if audio_mode == "Reactive":
        pulse = max(pulse, 1.0 + bass * .18)

    base = parse_color(settings.get("color", "#ffffff"))
    mode = settings.get("color_mode", "Rainbow")
    if mode == "Rainbow":
        base = hsv_color(t * 70 + bass * 40, .95, min(1.0, .82 + .18 * pulse))
    elif mode == "Audio":
        base = hsv_color(210 + mids * 150, .9, .60 + .40 * max(bass, mids, highs))
    elif pulse > 1.0:
        base = tuple(min(255, int(c * pulse)) for c in base)

    if settings.get("backplate"):
        pad = 2
        left = int(cx - w * scale / 2) - pad
        top = int(cy - h * scale / 2) - pad
        for py in range(max(0, top), min(display.height, top + h * scale + pad * 2)):
            for px in range(max(0, left), min(display.width, left + w * scale + pad * 2)):
                r,g,b = display.get_pixel(px, py)
                display.set_pixel(px, py, (int(r*.28), int(g*.28), int(b*.28)))

    _draw_sprite(
        display, name, cx, cy, scale, base,
        glow=bool(settings.get("glow")),
        glitch=bool(settings.get("glitch")),
        seed=int(seed + t * 18),
    )

    if settings.get("beat_pulse") and beat:
        renderer._beat_flash(display, .10 + bass * .16)


_base_original_render = performance_extras._original_render
_base_static_auto = performance_extras._draw_static_auto


def _overlay_render(renderer, display, settings, t, signals=None, seed=0, clear_background=True):
    if _overlay[_side(seed)].get("type") == "Icon":
        return _render_icon(renderer, display, settings, t, signals, seed, clear_background)
    return _base_original_render(renderer, display, settings, t, signals, seed, clear_background)


def _overlay_static(renderer, display, settings, t, signals, seed, clear_background):
    if _overlay[_side(seed)].get("type") == "Icon":
        return _render_icon(renderer, display, settings, t, signals, seed, clear_background)
    return _base_static_auto(renderer, display, settings, t, signals, seed, clear_background)


performance_extras._original_render = _overlay_render
performance_extras._draw_static_auto = _overlay_static

_base_get_commands = controller_state_ui.PhoneControlServer.get_commands


def _get_commands(self):
    commands = list(_base_get_commands(self))
    target = getattr(performance_extras, "_target", "both")
    for data in commands:
        if not isinstance(data, dict):
            continue
        if data.get("command") == "set_target" and data.get("value") in ("front", "back", "both"):
            target = data.get("value")
        if data.get("command") in ("text_settings", "text_show", "text_refresh"):
            value = data.get("value")
            if not isinstance(value, dict):
                continue
            sides = ("front", "back") if target == "both" else (target,)
            overlay_type = value.get("overlay_type")
            icon = value.get("overlay_icon")
            motion = value.get("overlay_motion")
            for side in sides:
                if overlay_type in ("Text", "Icon"):
                    _overlay[side]["type"] = overlay_type
                if icon in OVERLAY_ICONS:
                    _overlay[side]["icon"] = icon
                if motion in ("Static", "Float", "Bounce"):
                    _overlay[side]["motion"] = motion
    return commands


controller_state_ui.PhoneControlServer.get_commands = _get_commands

_base_update_state = controller_state_ui.PhoneControlServer.update_state


def _update_state(self, state):
    if isinstance(state, dict):
        state = dict(state)
        panels = dict(state.get("panels") or {})
        for side in ("front", "back"):
            panel = dict(panels.get(side) or {})
            text = dict(panel.get("text") or {})
            text["overlay_type"] = _overlay[side]["type"]
            text["overlay_icon"] = _overlay[side]["icon"]
            text["overlay_motion"] = _overlay[side]["motion"]
            panel["text"] = text
            panels[side] = panel
        state["panels"] = panels
        ref = state.get("reference_side", "front")
        if isinstance(state.get("text"), dict):
            t = dict(state["text"])
            t["overlay_type"] = _overlay[ref]["type"]
            t["overlay_icon"] = _overlay[ref]["icon"]
            t["overlay_motion"] = _overlay[ref]["motion"]
            state["text"] = t
        state["overlay_icons"] = list(OVERLAY_ICONS)
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state
