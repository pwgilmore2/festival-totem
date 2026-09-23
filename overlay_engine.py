import math
import random
import time

from text_engine import TextRenderer, clamp01, hsv_color, parse_color


class OverlayRenderer:
    """Native final-frame overlay compositor.

    Icons render from authored 32x32 masters 1:1. Text layout is automatic:
    static one-line, static two-line, then fast scroll. Text visuals are clean
    when audio reactivity is Off and derive their motion/pulse from the live
    music signal when Subtle or Reactive is selected.

    The icon source is dependency-injected so this module stays PIL-free and can
    run unchanged on both desktop and MatrixPortal.
    """

    def __init__(self, width, height, icon_library):
        self.width = width
        self.height = height
        self.icon_library = icon_library
        self.text = TextRenderer(width, height)
        self._text_clock = {
            "front": {"signature": None, "started": time.monotonic()},
            "back": {"signature": None, "started": time.monotonic()},
        }

    def _put(self, display, x, y, color):
        if 0 <= x < display.width and 0 <= y < display.height:
            display.set_pixel(x, y, color)

    def _icon_origin(self, state, t):
        x0 = (self.width - 32) // 2
        y0 = 0
        motion = state.get("motion", "Bounce")
        if motion == "Orbit":
            x0 += int(round(math.cos(t * 1.15) * 8.0))
            y0 += int(round(math.sin(t * 1.15) * 5.0))
        else:
            y0 += int(round(-abs(math.sin(t * 2.5)) * 2.0 + 1.0))
        return x0, y0

    def _transition(self, state, seed):
        if not state.get("transition_active"):
            return 1.0, None
        started = float(state.get("transition_started", 0.0))
        duration = max(0.08, float(state.get("transition_duration", 0.48)))
        p = max(0.0, min(1.0, (time.monotonic() - started) / duration))
        entering = bool(state.get("transition_entering", True))
        amount = p if entering else 1.0 - p
        return amount, amount

    def draw_icon(self, display, state, text_settings, t, signals=None, seed=0, text_enabled=False):
        if not state or not state.get("icon_enabled"):
            return
        if text_enabled:
            return

        asset = self.icon_library.get(state.get("icon"))
        if asset is None:
            return

        signals = signals or {}
        rgba = asset.pixels
        x0, y0 = self._icon_origin(state, t)
        amount, reveal = self._transition(state, seed)

        bass = clamp01(signals.get("bass", 0.0))
        mids = clamp01(signals.get("mids", 0.0))
        beat = bool(signals.get("beat", False))
        audio_mode = text_settings.get("audio_reactivity", "Off")
        if audio_mode == "Subtle":
            y0 += int(round(math.sin(t * 5.0) * bass))
            if beat:
                y0 -= 1
        elif audio_mode == "Reactive":
            y0 += int(round(math.sin(t * 6.0) * bass * 1.5))
            x0 += int(round(math.sin(t * 3.1) * mids))
            if beat:
                y0 -= 1

        pixels = []
        for sy, row in enumerate(rgba):
            for sx, (r, g, b, a) in enumerate(row):
                if a == 0:
                    continue
                if reveal is not None:
                    rr = random.Random(seed + sy * 97 + sx * 193)
                    if rr.random() > reveal:
                        continue
                px = x0 + sx
                py = y0 + sy
                brightness = max(0.0, min(1.0, amount))
                color = (int(r * brightness), int(g * brightness), int(b * brightness))
                pixels.append((px, py, color))

        for px, py, color in pixels:
            self._put(display, px, py, color)

    def _split_two_lines(self, text, scale, font):
        words = text.split()
        if len(words) < 2:
            return None
        line_h = 7 * scale
        gap = max(2, scale)
        if line_h * 2 + gap > self.height - 2:
            return None
        best = None
        for i in range(1, len(words)):
            a = " ".join(words[:i])
            b = " ".join(words[i:])
            wa = self.text.text_width(a, scale, font)
            wb = self.text.text_width(b, scale, font)
            if wa <= self.width - 4 and wb <= self.width - 4:
                score = abs(wa - wb)
                if best is None or score < best[0]:
                    best = (score, a, b)
        return None if best is None else (best[1], best[2])

    def _text_layout(self, text, requested_scale, font):
        width = self.text.text_width(text, requested_scale, font)
        if width <= self.width - 4:
            return "single", requested_scale, (text,)
        lines = self._split_two_lines(text, requested_scale, font)
        if lines:
            return "double", requested_scale, lines
        return "scroll", requested_scale, (text,)

    def _text_time(self, seed, signature):
        side = "back" if int(seed or 0) >= 1000 else "front"
        clock = self._text_clock[side]
        if clock["signature"] != signature:
            clock["signature"] = signature
            clock["started"] = time.monotonic()
        return max(0.0, time.monotonic() - clock["started"])

    def draw_text(self, display, settings, t, signals=None, seed=0, bottom=False):
        signals = signals or {}
        text = str(settings.get("message", "") or "").upper()[:120]
        if not text:
            return

        font = settings.get("font", "Pixel")
        color_mode = settings.get("color_mode", "Rainbow")
        if color_mode == "Audio":
            color_mode = "Rainbow"
        requested_scale = max(1, min(3, int(settings.get("scale", 1))))
        if bottom:
            requested_scale = 1
        layout, scale, lines = self._text_layout(text, requested_scale, font)
        signature = (text, font, requested_scale, layout, scale)
        text_t = self._text_time(seed, signature)
        speed = 34.0

        bass = clamp01(signals.get("bass", 0.0))
        mids = clamp01(signals.get("mids", 0.0))
        highs = clamp01(signals.get("highs", 0.0))
        beat = bool(signals.get("beat", False))
        audio_mode = settings.get("audio_reactivity", "Off")
        if audio_mode not in ("Off", "Subtle", "Reactive"):
            audio_mode = "Off"

        base = parse_color(settings.get("color", "#ffffff"))
        pulse = 1.0
        if audio_mode == "Subtle":
            pulse = 1.0 + bass * 0.10 + (0.06 if beat else 0.0)
        elif audio_mode == "Reactive":
            pulse = 1.0 + bass * 0.24 + (0.16 if beat else 0.0)

        def draw_line(line, x, y, draw_backplate=True):
            width = self.text.text_width(line, scale, font)
            if draw_backplate and settings.get("backplate"):
                self.text._backplate(display, x, y, width, 7 * scale)

            glow_strength = 0.0
            if audio_mode == "Subtle":
                glow_strength = 0.10 + highs * 0.05
            elif audio_mode == "Reactive":
                glow_strength = 0.17 + highs * 0.12
            if glow_strength > 0:
                glow = tuple(min(255, int(c * glow_strength)) for c in base)
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.text._draw_text(display, line, x + ox, y + oy, glow, scale, font, color_mode, text_t, pulse)

            self.text._draw_text(display, line, x, y, base, scale, font, color_mode, text_t, pulse)

        if layout == "single":
            line = lines[0]
            width = self.text.text_width(line, scale, font)
            x = (self.width - width) // 2
            y = self.height - 7 * scale - 1 if bottom else (self.height - 7 * scale) // 2
        elif layout == "double":
            gap = max(2, scale)
            total_h = 14 * scale + gap
            y1 = self.height - total_h - 1 if bottom else (self.height - total_h) // 2
            y2 = y1 + 7 * scale + gap
            positions = []
            for line, y in zip(lines, (y1, y2)):
                width = self.text.text_width(line, scale, font)
                x = (self.width - width) // 2
                if audio_mode == "Subtle" and beat:
                    y -= 1
                elif audio_mode == "Reactive":
                    x += int(round(math.sin(text_t * 3.1) * mids * 1.5))
                    y += int(round(math.sin(text_t * 5.7) * bass * 1.5)) - (1 if beat else 0)
                positions.append((line, x, y, width))

            if settings.get("backplate"):
                left = max(0, min(x for _, x, _, _ in positions) - 2)
                right = min(self.width, max(x + width for _, x, _, width in positions) + 2)
                top = max(0, min(y for _, _, y, _ in positions) - 2)
                bottom_y = min(self.height, max(y + 7 * scale for _, _, y, _ in positions) + 2)
                for py in range(top, bottom_y):
                    for px in range(left, right):
                        r, g, b = display.get_pixel(px, py)
                        display.set_pixel(px, py, (int(r * .28), int(g * .28), int(b * .28)))

            for line, x, y, _ in positions:
                draw_line(line, x, y, draw_backplate=False)
            if audio_mode == "Reactive" and beat:
                self.text._beat_flash(display, .08 + bass * .10)
            return
        else:
            line = lines[0]
            width = self.text.text_width(line, scale, font)
            total = self.width + width
            x = self.width - (int(text_t * speed) % max(1, total))
            y = self.height - 7 * scale - 1 if bottom else (self.height - 7 * scale) // 2

        if audio_mode == "Subtle":
            y -= 1 if beat else 0
        elif audio_mode == "Reactive":
            x += int(round(math.sin(text_t * 3.1) * mids * 1.5))
            y += int(round(math.sin(text_t * 5.7) * bass * 1.5)) - (1 if beat else 0)
            if highs > .60:
                rng = random.Random(seed + int(text_t * 20))
                if rng.random() < highs * .12:
                    x += rng.choice((-1, 1))

        draw_line(line, x, y)
        if audio_mode == "Reactive" and beat:
            self.text._beat_flash(display, .08 + bass * .10)
