import math
import time

from text_engine import TextRenderer, clamp01, parse_color


def audio_brightness(mode, signals):
    """Shared brightness pulse; glyph geometry and icon colors stay intact."""
    bass = clamp01(signals.get("bass", 0))
    beat = bool(signals.get("beat", False))
    if mode == "Subtle":
        return min(1.0, .78 + bass * .16 + (.10 if beat else 0))
    if mode in ("Reactive", "Intense"):
        return min(1.0, .60 + bass * .30 + clamp01(signals.get("highs", 0)) * .08 + (.18 if beat else 0))
    return 1.0


class DissolveDisplay:
    """Blend only touched pixels into the live background, without a frame buffer."""
    def __init__(self, display, progress, seed=0, outgoing=False):
        self.display = display
        self.width, self.height = display.width, display.height
        self.progress = clamp01(progress)
        self.amount = 1 - self.progress if outgoing else self.progress
        self.seed, self.outgoing = seed, outgoing

    def get_pixel(self, x, y):
        return self.display.get_pixel(x, y)

    def set_pixel(self, x, y, color):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        # An integer hash replaces one Random instance per pixel per frame.
        value = ((x * 374761393 + y * 668265263 + self.seed * 1274126177) & 0xffffffff)
        value = ((value ^ (value >> 13)) * 1274126177) & 0xffffffff
        threshold = (value & 65535) / 65536.0
        if (threshold >= self.progress) != self.outgoing:
            return
        old = self.display.get_pixel(x, y)
        a = self.amount
        self.display.set_pixel(x, y, tuple(int(old[i] * (1-a) + color[i] * a) for i in range(3)))


class OverlayRenderer:
    """Native final-frame overlay compositor.

    Icons render from authored native-size masters 1:1. Text layout is automatic:
    static one-line, static two-line, then fast scroll. Static text shares icon motion; audio changes brightness without changing
    glyph geometry. Dissolves write directly into the live background.

    The icon source is dependency-injected so this module stays PIL-free and can
    run unchanged on both desktop and MatrixPortal.
    """

    def __init__(self, width, height, icon_library):
        self.width = width
        self.height = height
        self.icon_library = icon_library
        self.text = TextRenderer(width, height)
        self._text_clock = {"front": [], "back": []}

    def _put(self, display, x, y, color):
        if 0 <= x < display.width and 0 <= y < display.height:
            display.set_pixel(x, y, color)

    def _icon_origin(self, state, t, width=32, height=32, legacy_icon=True):
        x0 = (self.width - width) // 2
        y0 = (self.height - height) // 2
        legacy = legacy_icon and width == 32 and height == 32
        motion = state.get("motion", "Bounce")
        if motion == "Orbit":
            # Full-size/oversized canvases intentionally lose up to two extra
            # edge pixels as they move. Smaller canvases stay within the panel.
            dx = 8 if legacy else (2 if width >= self.width else min(8, x0, self.width - width - x0))
            dy = 5 if legacy else (2 if height >= self.height else min(5, y0, self.height - height - y0))
            x0 += int(round(math.cos(t * 1.15) * dx))
            y0 += int(round(math.sin(t * 1.15) * dy))
        else:
            bounce = int(round(-abs(math.sin(t * 2.5)) * 2.0 + 1.0))
            y0 += bounce if legacy or height >= self.height else max(-y0, min(bounce, self.height - height - y0))
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
        height = len(rgba)
        width = len(rgba[0]) if height else 0
        if not width:
            return
        x0, y0 = self._icon_origin(state, t, width, height)
        _, reveal = self._transition(state, seed)

        brightness = audio_brightness(text_settings.get("audio_reactivity", "Off"), signals)
        # The MatrixPortal backend can composite a cached transparent Bitmap
        # in native code. Keep the existing per-pixel path for fades, audio
        # brightness changes, desktop rendering, and rotated panels.
        if reveal is None and brightness == 1.0:
            blit_icon = getattr(display, "blit_icon", None)
            if blit_icon is not None and blit_icon(asset, x0, y0):
                return
        if reveal is not None:
            display = DissolveDisplay(display, reveal, seed)
        for sy, row in enumerate(rgba):
            for sx, (r, g, b, a) in enumerate(row):
                if a:
                    color = (int(r * brightness), int(g * brightness), int(b * brightness))
                    self._put(display, x0 + sx, y0 + sy, color)

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
        clocks = self._text_clock[side]
        clock = next((entry for entry in clocks if entry["signature"] == signature), None)
        if clock is None:
            clock = {"signature": signature, "started": time.monotonic()}
            clocks.append(clock)
            if len(clocks) > 2:
                clocks.pop(0)
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

        base = parse_color(settings.get("color", "#ffffff"))
        pulse = audio_brightness(settings.get("audio_reactivity", "Off"), signals)
        if "transition_progress" in settings:
            display = DissolveDisplay(display, settings["transition_progress"], seed,
                                      settings.get("transition_outgoing", False))

        def draw_line(line, x, y, draw_backplate=True):
            width = self.text.text_width(line, scale, font)
            if draw_backplate and settings.get("backplate"):
                self.text._backplate(display, x, y, width, 7 * scale)

            self.text._draw_text(display, line, x, y, base, scale, font, color_mode, text_t, pulse)

        if layout == "single":
            line = lines[0]
            width = self.text.text_width(line, scale, font)
            x, y = self._icon_origin(settings, t, width, 7 * scale, legacy_icon=False)
            if bottom:
                y = self.height - 7 * scale - 1
        elif layout == "double":
            gap = max(2, scale)
            total_h = 14 * scale + gap
            block_width = max(self.text.text_width(line, scale, font) for line in lines)
            block_x, y1 = self._icon_origin(settings, t, block_width, total_h, legacy_icon=False)
            if bottom:
                y1 = self.height - total_h - 1
            y2 = y1 + 7 * scale + gap
            positions = []
            for line, y in zip(lines, (y1, y2)):
                width = self.text.text_width(line, scale, font)
                x = block_x + (block_width - width) // 2
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
            return
        else:
            line = lines[0]
            width = self.text.text_width(line, scale, font)
            total = self.width + width
            x = self.width - (int(text_t * speed) % max(1, total))
            y = self.height - 7 * scale - 1 if bottom else (self.height - 7 * scale) // 2

        draw_line(line, x, y)
