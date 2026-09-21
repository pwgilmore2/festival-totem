import math
import random
import time

import ui_cleanup_server
from text_engine import TextRenderer, parse_color, hsv_color, clamp01
from visual_engine import VisualLayerEngine, TransitionManager, copy_pixels

_target = "both"
_audio = {"bass": 0.0, "beat": False, "volume": 0.0}
_chaos_mode = None
_chaos_started = 0.0
_delayed_commands = []
_text_transitions = {
    "front": None,
    "back": None,
}
_text_started = {
    "front": time.monotonic(),
    "back": time.monotonic(),
}


def _target_sides():
    return ("front", "back") if _target == "both" else (_target,)


def _reset_text_clock(sides=None):
    now = time.monotonic()
    for side in sides or _target_sides():
        _text_started[side] = now


def _start_text_transition(entering):
    now = time.monotonic()
    style = random.choice(("fade", "drop", "scatter"))
    duration = random.uniform(0.42, 0.72)
    for side in _target_sides():
        _text_transitions[side] = {
            "entering": entering,
            "style": style,
            "start": now,
            "duration": duration,
        }
    return duration


def _finish_text_transition(sides=None):
    for side in sides or _target_sides():
        _text_transitions[side] = None


def _side_from_seed(seed):
    return "back" if int(seed or 0) >= 1000 else "front"


def _blend(a, b, amount):
    amount = max(0.0, min(1.0, amount))
    return tuple(int(a[i] + (b[i] - a[i]) * amount) for i in range(3))


def _split_two_lines(renderer, text, font):
    words = text.split()
    if len(words) < 2:
        return None
    best = None
    for i in range(1, len(words)):
        a = " ".join(words[:i])
        b = " ".join(words[i:])
        wa = renderer.text_width(a, 1, font)
        wb = renderer.text_width(b, 1, font)
        if wa <= renderer.width - 4 and wb <= renderer.width - 4:
            score = abs(wa - wb)
            if best is None or score < best[0]:
                best = (score, a, b)
    return None if best is None else (best[1], best[2])


def _draw_static_auto(renderer, display, settings, t, signals, seed, clear_background):
    signals = signals or {}
    text = str(settings.get("message", "") or " ").upper()[:120]
    font = settings.get("font", "Pixel")
    color_mode = settings.get("color_mode", "Rainbow")
    requested_scale = max(1, min(3, int(settings.get("scale", 1))))
    beat = bool(signals.get("beat", False))
    bass = clamp01(signals.get("bass", 0.0))
    mids = clamp01(signals.get("mids", 0.0))
    highs = clamp01(signals.get("highs", 0.0))

    if clear_background:
        display.clear()

    scale = requested_scale
    while scale > 1 and renderer.text_width(text, scale, font) > renderer.width - 4:
        scale -= 1

    pulse = 1.35 if settings.get("beat_pulse") and beat else 1.0
    base = parse_color(settings.get("color", "#ffffff"))
    if color_mode == "Audio":
        base = hsv_color(210 + mids * 130 + bass * 30, .85, .65 + .35 * max(bass, mids, highs))

    def draw_line(line, x, y, line_scale):
        width = renderer.text_width(line, line_scale, font)
        if settings.get("backplate"):
            renderer._backplate(display, x, y, width, 7 * line_scale)
        if settings.get("glow"):
            glow = tuple(int(c * .22) for c in base)
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                renderer._draw_text(display, line, x + ox, y + oy, glow, line_scale, font, color_mode, t, pulse)
        renderer._draw_text(display, line, x, y, base, line_scale, font, color_mode, t, pulse)

    width = renderer.text_width(text, scale, font)
    if width <= renderer.width - 4:
        x = (renderer.width - width) // 2
        y = (renderer.height - 7 * scale) // 2
        if settings.get("wave"):
            y += int(round(math.sin(t * 4.0) * 2))
        draw_line(text, x, y, scale)
    else:
        lines = _split_two_lines(renderer, text, font)
        if lines:
            a, b = lines
            gap = 3
            total_h = 7 + gap + 7
            y1 = (renderer.height - total_h) // 2
            y2 = y1 + 7 + gap
            draw_line(a, (renderer.width - renderer.text_width(a, 1, font)) // 2, y1, 1)
            draw_line(b, (renderer.width - renderer.text_width(b, 1, font)) // 2, y2, 1)
        else:
            fallback = dict(settings)
            fallback["motion"] = "Scroll Left"
            fallback["scale"] = 1
            fallback["speed"] = min(8.0, float(settings.get("speed", 8.0)))
            _original_render(renderer, display, fallback, t, signals, seed, clear_background=False)
            return

    if settings.get("beat_pulse") and beat:
        renderer._beat_flash(display, .10 + bass * .18)


# Text defaults: 2x and the new Medium speed.
_original_defaults = TextRenderer.defaults


def _defaults(self):
    st = _original_defaults(self)
    st["scale"] = 2
    st["speed"] = 22.0
    st["background"] = "Dimmed GIF"
    st["background_brightness"] = .30
    st["backplate"] = True
    return st


TextRenderer.defaults = _defaults

_original_render = TextRenderer.render


def _render(self, display, settings, t, signals=None, seed=0, clear_background=True):
    side = _side_from_seed(seed)
    text_t = max(0.0, time.monotonic() - _text_started[side])
    base_pixels = copy_pixels(display)

    if settings.get("motion") == "Static":
        _draw_static_auto(self, display, settings, text_t, signals, seed, clear_background)
    else:
        _original_render(self, display, settings, text_t, signals, seed, clear_background)

    tr = _text_transitions.get(side)
    if not tr:
        return
    p = (time.monotonic() - tr["start"]) / max(.01, tr["duration"])
    if p >= 1.0:
        _text_transitions[side] = None
        return
    p = max(0.0, min(1.0, p))
    amount = p if tr["entering"] else 1.0 - p
    final = copy_pixels(display)
    style = tr["style"]
    rng = random.Random(int(tr["start"] * 1000) + (1000 if side == "back" else 0))
    for y in range(display.height):
        for x in range(display.width):
            local = amount
            if style == "drop":
                delay = (x / max(1, display.width - 1)) * .28
                local = max(0.0, min(1.0, (amount - delay) / .72))
            elif style == "scatter":
                threshold = rng.random() * .72
                local = max(0.0, min(1.0, (amount - threshold) / .28))
            display.set_pixel(x, y, _blend(base_pixels[y][x], final[y][x], local))


TextRenderer.render = _render


# Pause slideshow transitions under the most destructive held effects. The next
# transition is allowed to continue as soon as the finger is released.
_original_transition_update = TransitionManager.update


def _transition_update(self, dt):
    if _chaos_mode in ("pixelmelt", "jumble", "bassjostle"):
        return
    _original_transition_update(self, dt)


TransitionManager.update = _transition_update


_original_guest_burst = VisualLayerEngine.guest_burst


def _row_wave(engine, display, amount, frame, tint=None):
    src = copy_pixels(display)
    amp = 1 + int(amount * 6)
    for y in range(display.height):
        shift = int(math.sin(y * .45 + frame * .12) * amp)
        for x in range(display.width):
            sx = max(0, min(display.width - 1, x - shift))
            r, g, b = src[y][sx]
            if tint == "teal":
                r = int(r * .34)
                g = min(255, int(g * 1.04 + b * .20))
                b = min(255, int(b * 1.13 + g * .06))
            display.set_pixel(x, y, (r, g, b))


def _pixel_melt(display, amount, frame):
    src = copy_pixels(display)
    elapsed = max(0.0, time.monotonic() - _chaos_started)
    strength = min(1.0, elapsed * .42) * amount
    rng = random.Random(4107)
    for x in range(display.width):
        speed = .35 + rng.random() * .9
        drop = int(strength * speed * (display.height + 12))
        wobble = int(math.sin(frame * .08 + x * .7) * amount * 2)
        for y in range(display.height):
            sy = y - drop - wobble
            if sy < 0:
                display.set_pixel(x, y, (0, 0, 0))
            else:
                display.set_pixel(x, y, src[min(display.height - 1, sy)][x])


def _jumble(display, amount, frame):
    src = copy_pixels(display)
    block = 4
    cols = max(1, display.width // block)
    rows = max(1, display.height // block)
    rng = random.Random((frame // 5) + 7301)
    swaps = int(2 + amount * cols * rows * .45)
    mapping = list(range(cols * rows))
    for _ in range(swaps):
        a = rng.randrange(len(mapping)); b = rng.randrange(len(mapping))
        mapping[a], mapping[b] = mapping[b], mapping[a]
    for by in range(rows):
        for bx in range(cols):
            src_index = mapping[by * cols + bx]
            sx0 = (src_index % cols) * block
            sy0 = (src_index // cols) * block
            for oy in range(block):
                for ox in range(block):
                    x = bx * block + ox; y = by * block + oy
                    if x < display.width and y < display.height:
                        display.set_pixel(x, y, src[min(display.height - 1, sy0 + oy)][min(display.width - 1, sx0 + ox)])


def _guest_burst(self, display, kind, amount, frame_number=0):
    mode = _chaos_mode if kind == "chaos" and _chaos_mode else kind
    amount = max(0.0, min(1.0, float(amount)))
    if mode in ("glitch", "rainbow", "chaos"):
        return _original_guest_burst(self, display, mode, amount, frame_number)
    if mode == "pixelmelt":
        _pixel_melt(display, amount, frame_number); return
    if mode == "jumble":
        _jumble(display, amount, frame_number); return
    if mode == "bassjostle":
        bass = max(0.0, min(1.0, float(_audio.get("bass", 0))))
        hit = 1.0 if _audio.get("beat") else .0
        power = amount * min(1.0, bass * 1.45 + hit * .45)
        self._shift(display, int(math.sin(frame_number * 1.9) * power * 9), int(math.cos(frame_number * 1.45) * power * 6))
        self._rgb_split(display, power * .5)
        if hit: self._zoom(display, power * .16)
        return
    if mode == "trance":
        wave = .5 + .5 * math.sin(frame_number * .06)
        self._zoom(display, (.05 + wave * .11) * amount)
        _row_wave(self, display, (.35 + wave * .45) * amount, frame_number, "teal")
        self._rgb_split(display, .06 + wave * .15 * amount)
        return
    if mode == "liquid":
        _row_wave(self, display, amount, frame_number)
        self._hue(display, math.sin(frame_number * .05) * 90 * amount)
        return
    if mode == "tunnel":
        wave = .5 + .5 * math.sin(frame_number * .12)
        self._zoom(display, (.12 + .30 * wave) * amount)
        self._rgb_split(display, (.08 + .32 * (1-wave)) * amount)
        self._hue(display, frame_number * 3.5 * amount)
        return
    return _original_guest_burst(self, display, kind, amount, frame_number)


VisualLayerEngine.guest_burst = _guest_burst


class PhoneControlServer(ui_cleanup_server.PhoneControlServer):
    def get_commands(self):
        global _target, _audio, _chaos_mode, _chaos_started
        commands = list(super().get_commands())
        now = time.monotonic()

        # Delayed commands carry an internal completion marker so they pass through
        # exactly once instead of re-scheduling the same text exit forever.
        ready = [item for item in _delayed_commands if item[0] <= now]
        if ready:
            commands.extend(item[1] for item in ready)
            _delayed_commands[:] = [item for item in _delayed_commands if item[0] > now]

        out = []
        for data in commands:
            if not isinstance(data, dict):
                out.append(data); continue
            c = data.get("command"); v = data.get("value")
            if c == "set_target" and v in ("front", "back", "both"):
                _target = v
            elif c == "audio_frame" and isinstance(v, dict):
                for key in ("bass", "volume"):
                    try: _audio[key] = max(0.0, min(1.0, float(v.get(key, _audio[key]))))
                    except Exception: pass
                _audio["beat"] = bool(v.get("beat", False))
            elif c == "text_show":
                _reset_text_clock()
                _start_text_transition(True)
            elif c == "text_hide":
                if data.get("_text_transition_complete"):
                    _finish_text_transition()
                    data = {k: val for k, val in data.items() if k != "_text_transition_complete"}
                else:
                    duration = _start_text_transition(False)
                    delayed = dict(data)
                    delayed["_text_transition_complete"] = True
                    _delayed_commands.append((now + duration, delayed))
                    continue
            elif c == "guest_action" and isinstance(v, dict):
                kind = str(v.get("kind", "")).lower()
                if kind in ("pixelmelt", "jumble", "bassjostle", "trance", "liquid", "tunnel"):
                    _chaos_mode = kind
                    _chaos_started = now
                    nv = dict(v); nv["kind"] = "chaos"
                    data = dict(data); data["value"] = nv
                else:
                    _chaos_mode = None
                    _chaos_started = now
            elif c == "guest_xy":
                _chaos_mode = None
            elif c == "guest_stop":
                _chaos_mode = None
            out.append(data)
        return out
