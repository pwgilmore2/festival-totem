import math
import random

import controller_state_ui
import performance_extras
from overlay_sprite_assets import OVERLAY_ICONS, SPRITES
from text_engine import TextRenderer, clamp01

_overlay = {
    "front": {"icon_enabled": False, "icon": "Heart", "motion": "Static", "text_visible": False},
    "back": {"icon_enabled": False, "icon": "Heart", "motion": "Static", "text_visible": False},
}


def _side(seed):
    return "back" if int(seed or 0) >= 1000 else "front"


def _sprite(name):
    return SPRITES.get(name, SPRITES["Heart"])


def _dims(name):
    rows = _sprite(name)["rows"]
    return max(len(r) for r in rows), len(rows)


def _put(display, x, y, color):
    if 0 <= x < display.width and 0 <= y < display.height:
        display.set_pixel(x, y, color)


def _tint(color, amount):
    if amount <= 0:
        return color
    boost = 1.0 + amount
    return tuple(min(255, int(c * boost)) for c in color)


def _palette_index(ch):
    # Full-detail masters use printable ASCII starting at '!'.
    return ord(ch) - 33


def _draw_sprite(display, name, cx, cy, target_h, glow=False, glitch=False, pulse=0.0, seed=0):
    data = _sprite(name)
    rows = data["rows"]
    palette = data["palette"]
    sw, sh = _dims(name)
    target_h = max(6, min(display.height, int(round(target_h))))
    target_w = max(6, int(round(sw * target_h / max(1, sh))))
    x0 = int(round(cx - target_w / 2))
    y0 = int(round(cy - target_h / 2))
    rng = random.Random(seed)

    pixels = []
    for ty in range(target_h):
        sy = min(sh - 1, int(ty * sh / target_h))
        row = rows[sy]
        for tx in range(target_w):
            sx = min(sw - 1, int(tx * sw / target_w))
            if sx >= len(row):
                continue
            ch = row[sx]
            if ch == ".":
                continue
            idx = _palette_index(ch)
            if idx < 0 or idx >= len(palette):
                continue
            px = x0 + tx
            py = y0 + ty
            if glitch and rng.random() < .06:
                px += rng.choice((-2, -1, 1, 2))
            pixels.append((px, py, _tint(palette[idx], pulse)))

    if glow:
        for px, py, color in pixels:
            g = tuple(max(8, int(c * .26)) for c in color)
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                _put(display, px + ox, py + oy, g)
    for px, py, color in pixels:
        _put(display, px, py, color)


def _icon_layout(renderer, settings, name, text_visible):
    message = str(settings.get("message", "") or "").strip() if text_visible else ""
    if not message:
        # Deliberately large: use almost the full 32px panel height.
        return renderer.width / 2, renderer.height / 2, 30

    motion = str(settings.get("motion", "Static"))
    if motion == "Static" and len(message) <= 10:
        return renderer.width / 2, 7.0, 13
    return 8.0, renderer.height / 2, 14


def _render_icon_layer(renderer, display, settings, t, signals=None, seed=0):
    signals = signals or {}
    side = _side(seed)
    st = _overlay[side]
    if not st.get("icon_enabled"):
        return

    name = st.get("icon", "Heart")
    cx, cy, target_h = _icon_layout(renderer, settings, name, st.get("text_visible", False))
    bass = clamp01(signals.get("bass", 0.0))
    mids = clamp01(signals.get("mids", 0.0))
    beat = bool(signals.get("beat", False))
    audio_mode = settings.get("audio_reactivity", "Off")
    speed = max(1.0, min(40.0, float(settings.get("speed", 22.0))))
    rate = speed / 22.0

    motion = st.get("motion", "Static")
    if motion == "Float":
        cx += math.sin(t * 1.35 * rate) * 2.0
        cy += math.cos(t * 1.05 * rate) * 1.5
    elif motion == "Bounce":
        cy += -abs(math.sin(t * 2.5 * rate)) * 3.0 + 1.5

    if audio_mode == "Subtle":
        target_h += bass * 1.0
        if beat:
            cy -= 1
    elif audio_mode == "Reactive":
        target_h += bass * 2.0
        cx += math.sin(t * 3.1) * mids * 1.5
        if beat:
            cy -= 2

    pulse = .14 if settings.get("beat_pulse") and beat else 0.0
    if audio_mode == "Reactive":
        pulse = max(pulse, bass * .12)

    _draw_sprite(
        display, name, cx, cy, target_h,
        glow=bool(settings.get("glow")),
        glitch=bool(settings.get("glitch")),
        pulse=pulse,
        seed=int(seed + t * 18),
    )


# Compose at the final TextRenderer entry point exactly once.
_base_text_render = TextRenderer.render


def _render_with_overlay(self, display, settings, t, signals=None, seed=0, clear_background=True):
    side = _side(seed)
    st = _overlay[side]
    adjusted = dict(settings)

    if st.get("text_visible"):
        if st.get("icon_enabled") and str(adjusted.get("message", "") or "").strip():
            adjusted["scale"] = 1
        _base_text_render(self, display, adjusted, t, signals, seed, clear_background)
    # When text is hidden we intentionally leave the already-rendered GIF alone.
    _render_icon_layer(self, display, adjusted, t, signals, seed)


TextRenderer.render = _render_with_overlay

_base_get_commands = controller_state_ui.PhoneControlServer.get_commands


def _get_commands(self):
    commands = list(_base_get_commands(self))
    target = getattr(performance_extras, "_target", "both")
    for data in commands:
        if not isinstance(data, dict):
            continue
        if data.get("command") == "set_target" and data.get("value") in ("front", "back", "both"):
            target = data.get("value")
        if data.get("command") not in ("text_settings", "text_show", "text_refresh"):
            continue
        value = data.get("value")
        if not isinstance(value, dict):
            continue
        sides = ("front", "back") if target == "both" else (target,)
        icon = value.get("overlay_icon")
        enabled = value.get("overlay_icon_enabled")
        motion = value.get("overlay_motion")
        text_visible = value.get("overlay_text_visible")
        for side in sides:
            if isinstance(enabled, bool):
                _overlay[side]["icon_enabled"] = enabled
            if icon in OVERLAY_ICONS:
                _overlay[side]["icon"] = icon
            if motion in ("Static", "Float", "Bounce"):
                _overlay[side]["motion"] = motion
            if isinstance(text_visible, bool):
                _overlay[side]["text_visible"] = text_visible
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
            text["overlay_icon_enabled"] = bool(_overlay[side]["icon_enabled"])
            text["overlay_icon"] = _overlay[side]["icon"]
            text["overlay_motion"] = _overlay[side]["motion"]
            text["overlay_text_visible"] = bool(_overlay[side]["text_visible"])
            panel["text"] = text
            panels[side] = panel
        state["panels"] = panels
        ref = state.get("reference_side", "front")
        if isinstance(state.get("text"), dict):
            t = dict(state["text"])
            t["overlay_icon_enabled"] = bool(_overlay[ref]["icon_enabled"])
            t["overlay_icon"] = _overlay[ref]["icon"]
            t["overlay_motion"] = _overlay[ref]["motion"]
            t["overlay_text_visible"] = bool(_overlay[ref]["text_visible"])
            state["text"] = t
        state["overlay_icons"] = list(OVERLAY_ICONS)
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state
