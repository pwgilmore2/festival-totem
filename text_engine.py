try:
    import colorsys
except ImportError:  # CircuitPython does not ship CPython's colorsys module.
    from matrixportal_colorsys import colorsys
import math
import runtime_random as random

from text import FONT

TEXT_FONTS = ["Pixel", "Block", "Thin", "Arcade", "Quest"]
TEXT_MOTIONS = ["Static"]
TEXT_COLORS = ["Solid", "Rainbow", "Audio"]
TEXT_EFFECTS = ["Glow", "Glitch", "Beat Pulse"]
TEXT_BACKGROUNDS = ["Black", "Dimmed GIF", "Tinted GIF"]
TEXT_AUDIO_MODES = ["Off", "Subtle", "Reactive"]


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
            "motion": "Static",
            "color_mode": "Rainbow",
            "color": "#ffffff",
            "scale": 1,
            "speed": 34.0,
            "glow": False,
            "wave": False,
            "glitch": False,
            "beat_pulse": True,
            "audio_reactivity": "Off",
            "background": "Black",
            "background_brightness": 0.65,
            "backplate": True,
        }

    def text_width(self, text, scale=1, font="Pixel"):
        glyph_w = 5 * scale
        spacing = self._spacing(scale, font)
        return max(0, len(text) * (glyph_w + spacing) - spacing)

    def prepare_background(self, display, settings):
        mode = settings.get("background", "Black")
        if mode == "Black":
            display.clear()
            return
        brightness = max(0.05, min(0.85, float(settings.get("background_brightness", 0.65))))
        if mode != "Tinted GIF" and hasattr(display, "dim"):
            display.dim(brightness)
            return
        tint = parse_color(settings.get("color", "#ffffff"))
        for y in range(display.height):
            for x in range(display.width):
                r, g, b = display.get_pixel(x, y)
                if mode == "Tinted GIF":
                    lum = (r + g + b) / (255.0 * 3.0)
                    display.set_pixel(x, y, (
                        int(tint[0] * lum * brightness),
                        int(tint[1] * lum * brightness),
                        int(tint[2] * lum * brightness),
                    ))
                else:
                    display.set_pixel(x, y, (int(r * brightness), int(g * brightness), int(b * brightness)))

    def render(self, display, settings, t, signals=None, seed=0, clear_background=True):
        signals = signals or {}
        text = str(settings.get("message", "") or " ").upper()[:120]
        font = settings.get("font", "Pixel")
        motion = settings.get("motion", "Static")
        color_mode = settings.get("color_mode", "Rainbow")
        scale = max(1, min(3, int(settings.get("scale", 1))))
        speed = max(1.0, min(40.0, float(settings.get("speed", 34.0))))
        beat = bool(signals.get("beat", False))
        bass = clamp01(signals.get("bass", 0.0))
        mids = clamp01(signals.get("mids", 0.0))
        highs = clamp01(signals.get("highs", 0.0))
        audio_mode = settings.get("audio_reactivity", "Off")

        if clear_background:
            display.clear()
        width = self.text_width(text, scale, font)
        text_h = 7 * scale
        x, y = self._position(motion, width, text_h, t, speed)

        if settings.get("wave"):
            y += int(round(math.sin(t * 3.8) * 2.0))

        if audio_mode == "Subtle":
            y += int(round(math.sin(t * 5.1) * bass * 1.6))
            if beat:
                y -= 1
        elif audio_mode == "Reactive":
            y += int(round(math.sin(t * 6.0) * bass * 3.2))
            x += int(round(math.sin(t * 3.2) * mids * 1.4))
            if beat:
                y -= 2
            if highs > .45:
                rng = random.Random(seed + int(t * 20))
                if rng.random() < highs * .35:
                    x += rng.choice((-1, 1))

        if settings.get("glitch") and highs > .18:
            rng = random.Random(seed + int(t * 18))
            x += rng.randint(-2, 2) if rng.random() < highs else 0
            y += rng.randint(-1, 1) if rng.random() < highs * .8 else 0

        pulse = 1.0
        if settings.get("beat_pulse") and beat:
            pulse = 1.35
        if audio_mode == "Subtle":
            pulse = max(pulse, 1.0 + bass * .08)
        elif audio_mode == "Reactive":
            pulse = max(pulse, 1.0 + bass * .18 + (0.12 if beat else 0.0))

        base = parse_color(settings.get("color", "#ffffff"))
        if color_mode == "Audio":
            base = hsv_color(210 + mids * 130 + bass * 30, .85, .65 + .35 * max(bass, mids, highs))
        elif audio_mode == "Reactive" and mids > .08:
            tint = hsv_color(260 + mids * 120, .72, 1.0)
            mix = mids * .24
            base = tuple(int(base[i] * (1.0 - mix) + tint[i] * mix) for i in range(3))

        if settings.get("backplate"):
            self._backplate(display, x, y, width, text_h)

        if settings.get("glow"):
            glow_strength = .22
            if audio_mode == "Subtle":
                glow_strength += bass * .06
            elif audio_mode == "Reactive":
                glow_strength += bass * .16 + highs * .08
            glow = tuple(min(255, int(c * glow_strength)) for c in base)
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self._draw_text(display, text, x + ox, y + oy, glow, scale, font, color_mode, t, pulse)

        self._draw_text(display, text, x, y, base, scale, font, color_mode, t, pulse)

        if settings.get("beat_pulse") and beat:
            flash = .10 + bass * .18
            if audio_mode == "Reactive":
                flash += .08
            self._beat_flash(display, flash)

    def _backplate(self, display, x, y, width, text_h):
        left = max(0, x - 2)
        right = min(display.width, x + width + 2)
        top = max(0, y - 2)
        bottom = min(display.height, y + text_h + 2)
        for py in range(top, bottom):
            for px in range(left, right):
                r, g, b = display.get_pixel(px, py)
                display.set_pixel(px, py, (int(r * .28), int(g * .28), int(b * .28)))

    def _position(self, motion, width, text_h, t, speed):
        y = (self.height - text_h) // 2
        if motion == "Static":
            return (self.width - width) // 2, y
        total = self.width + width
        offset = int(t * speed) % max(1, total)
        return self.width - offset, y

    def _spacing(self, scale, font):
        if font == "Arcade":
            return max(2, scale + 1)
        if font == "Quest":
            return max(2, scale + (1 if scale > 1 else 0))
        return max(2, scale + 1)

    def _draw_text(self, display, text, x, y, base_color, scale, font, color_mode, t, pulse):
        cursor = x
        spacing = self._spacing(scale, font)
        for index, ch in enumerate(text):
            color = base_color
            if color_mode == "Rainbow":
                color = hsv_color(t * 75 + index * 28, .95, min(1.0, pulse))
            elif pulse != 1.0:
                color = tuple(min(255, int(c * pulse)) for c in base_color)
            self._draw_glyph(display, ch, cursor, y, color, scale, font)
            cursor += 5 * scale + spacing

    def _draw_glyph(self, display, ch, x, y, color, scale, font):
        pattern = FONT.get(ch, FONT["?"])
        if font == "Quest":
            shadow = tuple(max(0, int(c * .28)) for c in color)
            for row, line in enumerate(pattern):
                for col, pixel in enumerate(line):
                    if pixel == "1":
                        display.set_pixel(x + col * scale + 1, y + row * scale + 1, shadow)
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
                    elif font == "Quest":
                        if row in (0, 6) and col in (0, 4):
                            accent = tuple(min(255, int(c * 1.20)) for c in color)
                            display.set_pixel(px, py, accent)

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
