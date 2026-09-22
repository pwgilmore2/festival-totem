import math
import random

from icon_assets import ICON_LIBRARY
from text_engine import TextRenderer, clamp01, hsv_color, parse_color


class OverlayRenderer:
    """Native final-frame overlay compositor.

    Icons come from ``IconLibrary`` and render from authored 32x32 masters 1:1.
    Bounce is the standard icon motion; no icon scaling or morphology occurs.
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.text = TextRenderer(width, height)

    def _put(self, display, x, y, color):
        if 0 <= x < display.width and 0 <= y < display.height:
            display.set_pixel(x, y, color)

    def draw_icon(self, display, state, text_settings, t, signals=None, seed=0, text_enabled=False):
        if not state or not state.get("icon_enabled"):
            return

        # 32x32 icon mode and text mode are deliberately exclusive until
        # separately authored mini icons exist. The runtime state/UI makes this
        # explicit, so the renderer never rescales a full-size master.
        if text_enabled:
            return

        asset = ICON_LIBRARY.get(state.get("icon"))
        if asset is None:
            return

        signals = signals or {}
        rgba = asset.pixels

        # Exact 32x32 authored canvas, centered horizontally on a 64x32 panel.
        # Bounce/phone-audio motion translates whole pixels only.
        x0 = (self.width - 32) // 2
        y0 = 0
        speed = max(1.0, min(40.0, float(text_settings.get("speed", 22.0))))
        rate = speed / 22.0
        y0 += int(round(-abs(math.sin(t * 2.5 * rate)) * 2.0 + 1.0))

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

        pulse = .12 if text_settings.get("beat_pulse") and beat else 0.0
        glow = bool(text_settings.get("glow"))
        glitch = bool(text_settings.get("glitch"))
        rng = random.Random(seed + int(t * 18))

        pixels = []
        for sy, row in enumerate(rgba):
            for sx, (r, g, b, a) in enumerate(row):
                if a == 0:
                    continue
                px = x0 + sx
                py = y0 + sy
                if glitch and rng.random() < .05:
                    px += rng.choice((-1, 1))
                color = (r, g, b)
                if pulse:
                    color = tuple(min(255, int(c * (1.0 + pulse))) for c in color)
                pixels.append((px, py, color))

        if glow:
            for px, py, color in pixels:
                halo = tuple(max(8, int(c * .24)) for c in color)
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self._put(display, px + ox, py + oy, halo)
        for px, py, color in pixels:
            self._put(display, px, py, color)

    def draw_text(self, display, settings, t, signals=None, seed=0, bottom=False):
        """Draw text without clearing/replacing the underlying content."""
        signals = signals or {}
        text = str(settings.get("message", "") or "").upper()[:120]
        if not text:
            return

        font = settings.get("font", "Pixel")
        color_mode = settings.get("color_mode", "Rainbow")
        scale = max(1, min(3, int(settings.get("scale", 1))))
        speed = max(1.0, min(40.0, float(settings.get("speed", 22.0))))
        motion = settings.get("motion", "Scroll Left")
        if bottom:
            scale = 1

        width = self.text.text_width(text, scale, font)
        text_h = 7 * scale
        if motion == "Static" and width <= self.width - 2:
            x = (self.width - width) // 2
        else:
            total = self.width + width
            x = self.width - (int(t * speed) % max(1, total))
        y = self.height - text_h - 1 if bottom else (self.height - text_h) // 2

        bass = clamp01(signals.get("bass", 0.0))
        mids = clamp01(signals.get("mids", 0.0))
        highs = clamp01(signals.get("highs", 0.0))
        beat = bool(signals.get("beat", False))
        audio_mode = settings.get("audio_reactivity", "Off")
        if audio_mode == "Subtle":
            y -= 1 if beat else 0
        elif audio_mode == "Reactive":
            x += int(round(math.sin(t * 3.2) * mids))
            y -= 1 if beat else 0
            if highs > .55:
                rng = random.Random(seed + int(t * 20))
                if rng.random() < highs * .2:
                    x += rng.choice((-1, 1))

        base = parse_color(settings.get("color", "#ffffff"))
        if color_mode == "Audio":
            base = hsv_color(210 + mids * 130 + bass * 30, .85, .65 + .35 * max(bass, mids, highs))

        if settings.get("backplate"):
            self.text._backplate(display, x, y, width, text_h)
        if settings.get("glow"):
            glow = tuple(min(255, int(c * .22)) for c in base)
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self.text._draw_text(display, text, x + ox, y + oy, glow, scale, font, color_mode, t, 1.0)
        self.text._draw_text(display, text, x, y, base, scale, font, color_mode, t, 1.0)
