import colorsys
import math
import random

from text import FONT

TEXT_FONTS = ["Pixel", "Block", "Thin", "Arcade"]
TEXT_MOTIONS = ["Scroll Left", "Scroll Right", "Static", "Bounce"]
TEXT_COLORS = ["Solid", "Rainbow", "Audio"]
TEXT_EFFECTS = ["Glow", "Wave", "Glitch", "Beat Pulse"]


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def hsv_color(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, clamp01(s), clamp01(v))
    return int(r * 255), int(g * 255), int(b * 255)


def parse_color(value, fallback=(255, 255, 255)):
    if isinstance(value, str) and len(value) == 7 and value.startswith("#"):
        try:
            return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            pass
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return tuple(max(0, min(255, int(v))) for v in value[:3])
        except (TypeError, ValueError):
            pass
    return fallback


class TextRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def defaults(self):
        return {
            "message": "FESTIVAL MODE",
            "font": "Pixel",
            "motion": "Scroll Left",
            "color_mode": "Rainbow",
            "color": "#ffffff",
            "scale": 1,
            "speed": 12.0,
            "glow": False,
            "wave": False,
            "glitch": False,
            "beat_pulse": True,
        }

    def text_width(self, text, scale=1, font="Pixel"):
        glyph_w = 5 * scale
        spacing = self._spacing(scale, font)
        return max(0, len(text) * (glyph_w + spacing) - spacing)

    def render(self, display, settings, t, signals=None, seed=0):
        signals = signals or {}
        text = str(settings.get("message", "") or " ").upper()[:120]
        font = settings.get("font", "Pixel")
        motion = settings.get("motion", "Scroll Left")
        color_mode = settings.get("color_mode", "Rainbow")
        scale = max(1, min(3, int(settings.get("scale", 1))))
        speed = max(1.0, min(40.0, float(settings.get("speed", 12.0))))
        beat = bool(signals.get("beat", False))
        bass = clamp01(signals.get("bass", 0.0))
        mids = clamp01(signals.get("mids", 0.0))
        highs = clamp01(signals.get("highs", 0.0))

        display.clear()
        width = self.text_width(text, scale, font)
        text_h = 7 * scale
        x, y = self._position(motion, width, text_h, t, speed)
        if settings.get("wave"):
            y += int(round(math.sin(t * 4.0) * 2))
        if settings.get("glitch") and highs > .18:
            rng = random.Random(seed + int(t * 18))
            x += rng.randint(-2, 2) if rng.random() < highs else 0
            y += rng.randint(-1, 1) if rng.random() < highs * .8 else 0

        pulse = 1.0
        if settings.get("beat_pulse") and beat:
            pulse = 1.35

        base = parse_color(settings.get("color", "#ffffff"))
        if color_mode == "Audio":
            base = hsv_color(210 + mids * 130 + bass * 30, .85, .65 + .35 * max(bass, mids, highs))

        if settings.get("glow"):
            glow = tuple(int(c * .22) for c in base)
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self._draw_text(display, text, x + ox, y + oy, glow, scale, font, color_mode, t, pulse)

        self._draw_text(display, text, x, y, base, scale, font, color_mode, t, pulse)

        if settings.get("beat_pulse") and beat:
            self._beat_flash(display, .10 + bass * .18)

    def _position(self, motion, width, text_h, t, speed):
        y = (self.height - text_h) // 2
        if motion == "Static":
            return (self.width - width) // 2, y
        if motion == "Scroll Right":
            total = self.width + width
            offset = int(t * speed) % max(1, total)
            return -width + offset, y
        if motion == "Bounce":
            span = max(0, self.width - width)
            if span <= 0:
                total = self.width + width
                offset = int(t * speed) % max(1, total)
                return self.width - offset, y
            phase = (t * speed / max(1, span)) % 2.0
            pos = phase if phase <= 1 else 2 - phase
            return int(pos * span), y
        total = self.width + width
        offset = int(t * speed) % max(1, total)
        return self.width - offset, y

    def _spacing(self, scale, font):
        if font == "Block":
            return max(1, scale)
        if font == "Arcade":
            return max(1, scale + 1)
        return max(1, scale)

    def _draw_text(self, display, text, x, y, base_color, scale, font, color_mode, t, pulse):
        cursor = x
        spacing = self._spacing(scale, font)
        for index, ch in enumerate(text):
            color = base_color
            if color_mode == "Rainbow":
                color = hsv_color(t * 75 + index * 28, .95, min(1.0, pulse))
            elif pulse > 1.0:
                color = tuple(min(255, int(c * pulse)) for c in base_color)
            self._draw_glyph(display, ch, cursor, y, color, scale, font)
            cursor += 5 * scale + spacing

    def _draw_glyph(self, display, ch, x, y, color, scale, font):
        pattern = FONT.get(ch, FONT["?"])
        for row, line in enumerate(pattern):
            for col, pixel in enumerate(line):
                if pixel != "1":
                    continue
                px = x + col * scale
                py = y + row * scale
                if font == "Thin":
                    display.set_pixel(px, py, color)
                    if scale > 1:
                        display.set_pixel(px + scale - 1, py + scale - 1, color)
                else:
                    for sy in range(scale):
                        for sx in range(scale):
                            display.set_pixel(px + sx, py + sy, color)
                    if font == "Block":
                        display.set_pixel(px + scale, py, color)
                    elif font == "Arcade" and (row + col) % 2 == 0:
                        bright = tuple(min(255, int(c * 1.18)) for c in color)
                        display.set_pixel(px, py, bright)

    def _beat_flash(self, display, amount):
        amount = clamp01(amount)
        for y in range(display.height):
            for x in range(display.width):
                r, g, b = display.get_pixel(x, y)
                display.set_pixel(x, y, (
                    int(r + (255 - r) * amount),
                    int(g + (255 - g) * amount),
                    int(b + (255 - b) * amount),
                ))
