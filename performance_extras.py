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
_chaos_releasing = 0.0
_chaos_release_duration = 0.0
_xy = {"x": .5, "y": .5, "velocity": 0.0}
_delayed_commands = []
_text_transitions = {
    "front": None,
    "back": None,
}
_text_started = {
    "front": time.monotonic(),
    "back": time.monotonic(),
}

_CHILL_MODES = {"trance", "liquid", "tunnel", "warp", "prism", "rainbow"}


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


def _smooth01(v):
    v = max(0.0, min(1.0, float(v)))
    return v * v * (3.0 - 2.0 * v)


def _effect_envelope(mode):
    now = time.monotonic()
    if mode == "xyintent":
        ramp = .18
    elif mode in _CHILL_MODES:
        ramp = 2.4
    else:
        ramp = .12
    env = _smooth01((now - _chaos_started) / max(.01, ramp))
    if _chaos_releasing:
        release = (now - _chaos_releasing) / max(.01, _chaos_release_duration)
        env *= 1.0 - _smooth01(release)
    return max(0.0, min(1.0, env))


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

_original_transition_update = TransitionManager.update


def _transition_update(self, dt):
    if _chaos_mode in ("jumble", "bassjostle"):
        return
    _original_transition_update(self, dt)


TransitionManager.update = _transition_update

_original_guest_burst = VisualLayerEngine.guest_burst


def _row_wave(engine, display, amount, frame, tint=None, speed=.035, frequency=.34):
    src = copy_pixels(display)
    amp = max(1, int(1 + amount * 4))
    for y in range(display.height):
        shift = int(math.sin(y * frequency + frame * speed) * amp)
        for x in range(display.width):
            sx = max(0, min(display.width - 1, x - shift))
            r, g, b = src[y][sx]
            if tint == "teal":
                r = int(r * .48)
                g = min(255, int(g * 1.02 + b * .12))
                b = min(255, int(b * 1.08 + g * .04))
            display.set_pixel(x, y, (r, g, b))


def _pixel_melt(display, amount, frame):
    src = copy_pixels(display)
    elapsed = max(0.0, time.monotonic() - _chaos_started)
    strength = min(1.0, elapsed * .30) * amount
    rng = random.Random(4107)
    for x in range(display.width):
        speed = .35 + rng.random() * .9
        drop = int(strength * speed * (display.height + 6))
        wobble = int(math.sin(frame * .055 + x * .7) * amount)
        for y in range(display.height):
            sy = y - drop - wobble
            display.set_pixel(x, y, src[max(0, min(display.height - 1, sy))][x])


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
    amount = max(0.0, min(1.0, float(amount))) * _effect_envelope(mode)
    if amount <= .002:
        return
    if mode in ("glitch", "chaos"):
        return _original_guest_burst(self, display, mode, amount, frame_number)
    if mode == "rainbow":
        self._hue(display, math.sin(frame_number * .016) * 95 * amount)
        self._brighten(display, amount * .06)
        return
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
        wave = .5 + .5 * math.sin(frame_number * .025)
        self._zoom(display, (.025 + wave * .055) * amount)
        _row_wave(self, display, (.14 + wave * .20) * amount, frame_number, "teal", speed=.025)
        self._rgb_split(display, (.025 + wave * .065) * amount)
        return
    if mode == "liquid":
        wave = .5 + .5 * math.sin(frame_number * .022)
        _row_wave(self, display, (.16 + wave * .24) * amount, frame_number, speed=.022, frequency=.30)
        self._hue(display, math.sin(frame_number * .018) * 46 * amount)
        return
    if mode == "warp":
        wave = .5 + .5 * math.sin(frame_number * .022)
        self._zoom(display, (.025 + wave * .07) * amount)
        self._shift(display, int(math.sin(frame_number * .03) * amount * 2), int(math.cos(frame_number * .024) * amount))
        self._hue(display, math.sin(frame_number * .014) * 62 * amount)
        return
    if mode == "prism":
        wave = .5 + .5 * math.sin(frame_number * .024)
        self._rgb_split(display, (.055 + wave * .19) * amount)
        self._hue(display, math.sin(frame_number * .016) * 50 * amount)
        self._sparkles(display, amount * .08, frame_number * 7)
        return
    if mode == "tunnel":
        wave = .5 + .5 * math.sin(frame_number * .028)
        self._zoom(display, (.035 + .11 * wave) * amount)
        self._rgb_split(display, (.025 + .075 * (1-wave)) * amount)
        self._hue(display, math.sin(frame_number * .014) * 70 * amount)
        return
    if mode == "xyintent":
        x = max(0.0, min(1.0, float(_xy.get("x", .5))))
        y = max(0.0, min(1.0, float(_xy.get("y", .5))))
        dead = .10
        left = max(0.0, (-((x - .5)) - dead) / (.5 - dead))
        right = max(0.0, ((x - .5) - dead) / (.5 - dead))
        up = max(0.0, (-((y - .5)) - dead) / (.5 - dead))
        down = max(0.0, ((y - .5) - dead) / (.5 - dead))
        if up > 0:
            self._zoom(display, up * amount * .28)
        if down > 0:
            self._shift(display, int(math.sin(frame_number * 1.7) * down * amount * 6), int(math.cos(frame_number * 1.35) * down * amount * 4))
        if right > 0:
            self._rgb_split(display, right * amount * .85)
        if left > 0:
            self._rgb_split(display, left * amount * .32)
            self._shift(display, int(math.sin(frame_number * 2.5) * left * amount * 7), 0)
        return
    return _original_guest_burst(self, display, kind, amount, frame_number)


VisualLayerEngine.guest_burst = _guest_burst


class PhoneControlServer(ui_cleanup_server.PhoneControlServer):
    def get_commands(self):
        global _target, _audio, _chaos_mode, _chaos_started, _chaos_releasing, _chaos_release_duration, _xy
        commands = list(super().get_commands())
        now = time.monotonic()

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
                mapped = {"pixelmelt", "jumble", "bassjostle", "trance", "liquid", "tunnel", "warp", "prism", "rainbow"}
                if kind in mapped:
                    _chaos_mode = kind
                    _chaos_started = now
                    _chaos_releasing = 0.0
                    _chaos_release_duration = 0.0
                    nv = dict(v); nv["kind"] = "chaos"
                    data = dict(data); data["value"] = nv
                else:
                    _chaos_mode = None
                    _chaos_started = now
                    _chaos_releasing = 0.0
            elif c == "guest_xy" and isinstance(v, dict):
                try:
                    _xy = {"x": float(v.get("x", .5)), "y": float(v.get("y", .5)), "velocity": float(v.get("velocity", 0))}
                except Exception:
                    _xy = {"x": .5, "y": .5, "velocity": 0.0}
                if _chaos_mode != "xyintent":
                    _chaos_started = now
                _chaos_mode = "xyintent"
                _chaos_releasing = 0.0
                nv = {"kind": "chaos", "strength": v.get("strength", 1.0), "duration": .35}
                data = {"command": "guest_action", "value": nv}
            elif c == "guest_stop":
                if data.get("_guest_release_complete"):
                    _chaos_mode = None
                    _chaos_releasing = 0.0
                    _chaos_release_duration = 0.0
                    data = {k: val for k, val in data.items() if k != "_guest_release_complete"}
                elif _chaos_mode in _CHILL_MODES:
                    _chaos_releasing = now
                    _chaos_release_duration = .95
                    delayed = dict(data)
                    delayed["_guest_release_complete"] = True
                    _delayed_commands.append((now + _chaos_release_duration, delayed))
                    continue
                elif _chaos_mode == "xyintent":
                    _chaos_releasing = now
                    _chaos_release_duration = .32
                    delayed = dict(data)
                    delayed["_guest_release_complete"] = True
                    _delayed_commands.append((now + _chaos_release_duration, delayed))
                    continue
                else:
                    _chaos_mode = None
                    _chaos_releasing = 0.0
            out.append(data)
        return out
