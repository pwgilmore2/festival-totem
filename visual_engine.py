import math
import random


TRANSITIONS = ["Fade", "Melt", "Dissolve", "Glitch", "Ripple", "Zoom", "Wipe", "None"]
LAYER_KEYS = [
    "bass_zoom",
    "beat_flash",
    "mids_hue",
    "high_sparkle",
    "volume_brightness",
    "bass_shake",
    "high_rgb_split",
]


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def copy_pixels(display):
    return [row[:] for row in display.pixels]


def write_pixels(display, pixels):
    for y in range(display.height):
        for x in range(display.width):
            display.set_pixel(x, y, pixels[y][x])


def blend_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class TransitionManager:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.active = False
        self.kind = "Fade"
        self.duration = 0.8
        self.elapsed = 0.0
        self.source = None
        self.seed = 0

    def begin(self, display, kind="Fade", duration=0.8):
        if kind == "None" or duration <= 0:
            self.active = False
            self.source = None
            return
        self.kind = kind if kind in TRANSITIONS else "Fade"
        self.duration = max(0.08, min(5.0, float(duration)))
        self.elapsed = 0.0
        self.source = copy_pixels(display)
        self.seed = random.randrange(1_000_000)
        self.active = True

    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False
            self.source = None

    @property
    def progress(self):
        if not self.active or self.duration <= 0:
            return 1.0
        return clamp01(self.elapsed / self.duration)

    def apply(self, display):
        if not self.active or self.source is None:
            return
        target = copy_pixels(display)
        p = self.progress
        if self.kind == "Fade":
            self._fade(display, target, p)
        elif self.kind == "Melt":
            self._melt(display, target, p)
        elif self.kind == "Dissolve":
            self._dissolve(display, target, p)
        elif self.kind == "Glitch":
            self._glitch(display, target, p)
        elif self.kind == "Ripple":
            self._ripple(display, target, p)
        elif self.kind == "Zoom":
            self._zoom_transition(display, target, p)
        elif self.kind == "Wipe":
            self._wipe(display, target, p)

    def _fade(self, display, target, p):
        for y in range(self.height):
            for x in range(self.width):
                display.set_pixel(x, y, blend_color(self.source[y][x], target[y][x], p))

    def _melt(self, display, target, p):
        rng = random.Random(self.seed)
        column_offsets = [rng.uniform(0.0, 0.55) for _ in range(self.width)]
        for x in range(self.width):
            local = clamp01((p - column_offsets[x]) / max(0.08, 1.0 - column_offsets[x]))
            drop = int((local ** 1.6) * (self.height + 8))
            for y in range(self.height):
                src_y = y - drop
                if src_y >= 0 and local < 0.98:
                    old = self.source[src_y][x]
                    edge = clamp01(local * 1.25)
                    display.set_pixel(x, y, blend_color(old, target[y][x], edge * 0.45))
                else:
                    display.set_pixel(x, y, target[y][x])

    def _dissolve(self, display, target, p):
        rng = random.Random(self.seed)
        for y in range(self.height):
            for x in range(self.width):
                threshold = rng.random()
                display.set_pixel(x, y, target[y][x] if threshold <= p else self.source[y][x])

    def _glitch(self, display, target, p):
        rng = random.Random(self.seed + int(p * 30))
        old_weight = max(0.0, 1.0 - p)
        for y in range(self.height):
            band = rng.random() < (0.22 + old_weight * 0.38)
            shift = rng.randint(-10, 10) if band else 0
            for x in range(self.width):
                if rng.random() < p:
                    c = target[y][x]
                else:
                    sx = max(0, min(self.width - 1, x + shift))
                    c = self.source[y][sx]
                display.set_pixel(x, y, c)

    def _ripple(self, display, target, p):
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0
        max_r = math.hypot(cx, cy)
        radius = p * (max_r + 8)
        for y in range(self.height):
            for x in range(self.width):
                d = math.hypot(x - cx, y - cy)
                wave = 2.2 * math.sin((d - radius) * 1.25) * (1.0 - p)
                if d <= radius:
                    sx = int(round(cx + (x - cx) * (1.0 - wave * 0.018)))
                    sy = int(round(cy + (y - cy) * (1.0 - wave * 0.018)))
                    sx = max(0, min(self.width - 1, sx))
                    sy = max(0, min(self.height - 1, sy))
                    edge = clamp01((radius - d + 3) / 6.0)
                    display.set_pixel(x, y, blend_color(self.source[y][x], target[sy][sx], edge))
                else:
                    display.set_pixel(x, y, self.source[y][x])

    def _zoom_transition(self, display, target, p):
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0
        old_zoom = 1.0 + p * 1.5
        new_zoom = 1.85 - p * 0.85
        for y in range(self.height):
            for x in range(self.width):
                osx = int(round(cx + (x - cx) / old_zoom))
                osy = int(round(cy + (y - cy) / old_zoom))
                nsx = int(round(cx + (x - cx) / new_zoom))
                nsy = int(round(cy + (y - cy) / new_zoom))
                osx = max(0, min(self.width - 1, osx)); osy = max(0, min(self.height - 1, osy))
                nsx = max(0, min(self.width - 1, nsx)); nsy = max(0, min(self.height - 1, nsy))
                display.set_pixel(x, y, blend_color(self.source[osy][osx], target[nsy][nsx], p))

    def _wipe(self, display, target, p):
        edge = int(p * (self.width + 12)) - 6
        for y in range(self.height):
            wobble = int(math.sin(y * 0.55 + self.seed) * 3)
            for x in range(self.width):
                local = x - (edge + wobble)
                if local < -2:
                    display.set_pixel(x, y, target[y][x])
                elif local > 2:
                    display.set_pixel(x, y, self.source[y][x])
                else:
                    display.set_pixel(x, y, blend_color(target[y][x], self.source[y][x], clamp01((local + 2) / 4.0)))


class VisualLayerEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def default_layers(self):
        return {
            "bass_zoom": 0.20,
            "beat_flash": 0.24,
            "mids_hue": 0.0,
            "high_sparkle": 0.10,
            "volume_brightness": 0.08,
            "bass_shake": 0.0,
            "high_rgb_split": 0.0,
        }

    def preset(self, name):
        # The signal names remain stable for controller/backward compatibility,
        # but now represent musical controls: bass=Low novelty, mids=Body novelty,
        # highs=Bright novelty, volume=Energy and beat=Pulse.
        presets = {
            "Pulse": {
                "bass_zoom": .28,
                "beat_flash": .28,
                "mids_hue": 0,
                "high_sparkle": .02,
                "volume_brightness": .10,
                "bass_shake": .08,
                "high_rgb_split": 0,
            },
            "Neon": {
                "bass_zoom": .05,
                "beat_flash": .08,
                "mids_hue": .30,
                "high_sparkle": .05,
                "volume_brightness": .08,
                "bass_shake": 0,
                "high_rgb_split": .18,
            },
            "Spark": {
                "bass_zoom": .03,
                "beat_flash": .08,
                "mids_hue": .04,
                "high_sparkle": .55,
                "volume_brightness": .05,
                "bass_shake": 0,
                "high_rgb_split": .10,
            },
            "Chaos": {
                "bass_zoom": .26,
                "beat_flash": .35,
                "mids_hue": .32,
                "high_sparkle": .38,
                "volume_brightness": .15,
                "bass_shake": .25,
                "high_rgb_split": .32,
            },
        }
        return dict(presets.get(name, self.default_layers()))

    def apply(self, display, signals, layers, strength=1.0, frame_number=0, side_seed=0):
        bass = clamp01(signals.get("bass", 0)) * strength
        mids = clamp01(signals.get("mids", 0)) * strength
        highs = clamp01(signals.get("highs", 0)) * strength
        volume = clamp01(signals.get("volume", 0)) * strength
        beat = bool(signals.get("beat", False))
        tilt_x = max(-1.0, min(1.0, float(signals.get("tilt_x", 0.0))))
        tilt_y = max(-1.0, min(1.0, float(signals.get("tilt_y", 0.0))))
        shake = clamp01(signals.get("shake", 0.0))

        zoom_amount = bass * layers.get("bass_zoom", 0)
        dx = int((bass * layers.get("bass_shake", 0) * math.sin(frame_number * 1.7) + tilt_x * .15) * 8)
        dy = int((bass * layers.get("bass_shake", 0) * math.cos(frame_number * 1.3) + tilt_y * .15) * 5)
        self._spatial(display, zoom_amount, dx, dy)

        self._color_pipeline(
            display,
            mids * layers.get("mids_hue", 0) * 150,
            highs * layers.get("high_rgb_split", 0),
            volume * layers.get("volume_brightness", 0),
        )
        self._sparkles(display, highs * layers.get("high_sparkle", 0), frame_number + side_seed)
        if beat:
            self._flash(display, layers.get("beat_flash", 0) * strength)
        if shake > .15:
            self._shift(display, int(math.sin(frame_number * 2.1) * shake * 5), int(math.cos(frame_number * 1.8) * shake * 3))

    def guest_burst(self, display, kind, amount, frame_number=0):
        amount = clamp01(amount)
        if kind == "boom":
            self._zoom(display, amount * .38)
            self._flash(display, amount * .45)
        elif kind == "glitch":
            self._rgb_split(display, .3 + amount * .7)
            self._shift(display, int(math.sin(frame_number * 2.7) * amount * 8), 0)
        elif kind == "spark":
            self._sparkles(display, amount, frame_number * 19)
        elif kind == "rainbow":
            self._hue(display, (frame_number * 8) % 360)
            self._brighten(display, amount * .15)
        elif kind == "chaos":
            self._zoom(display, amount * .25)
            self._rgb_split(display, amount * .8)
            self._hue(display, frame_number * 11)
            self._sparkles(display, amount, frame_number * 31)

    def _spatial(self, display, zoom_amount, dx, dy):
        """Apply the normal zoom-then-shift chain with one source snapshot."""
        zoom_amount = max(0.0, float(zoom_amount))
        if zoom_amount <= .001 and dx == 0 and dy == 0:
            return
        src = copy_pixels(display)
        zoom = 1.0 + zoom_amount
        cx = (self.width - 1) / 2
        cy = (self.height - 1) / 2
        for y in range(self.height):
            ty = max(0, min(self.height - 1, y - dy))
            for x in range(self.width):
                tx = max(0, min(self.width - 1, x - dx))
                if zoom_amount > .001:
                    sx = int(round(cx + (tx - cx) / zoom))
                    sy = int(round(cy + (ty - cy) / zoom))
                    sx = max(0, min(self.width - 1, sx))
                    sy = max(0, min(self.height - 1, sy))
                else:
                    sx, sy = tx, ty
                display.set_pixel(x, y, src[sy][sx])

    def _color_pipeline(self, display, degrees, split_amount, brighten_amount):
        """Fuse hue -> RGB split -> brightness into one full-frame pass."""
        hue_active = abs(degrees) >= .5
        split_active = split_amount > .02
        brighten_active = brighten_amount > .001
        if not (hue_active or split_active or brighten_active):
            return

        mult = 1.0 + max(0.0, float(brighten_amount))
        if not hue_active and not split_active:
            for y in range(self.height):
                for x in range(self.width):
                    r, g, b = display.get_pixel(x, y)
                    display.set_pixel(x, y, (min(255, int(r * mult)), min(255, int(g * mult)), min(255, int(b * mult))))
            return

        src = copy_pixels(display)
        offset = max(1, int(round(split_amount * 5))) if split_active else 0
        phase = (degrees % 360) / 120.0 if hue_active else 0.0
        t = phase if phase < 1 else phase - 1 if phase < 2 else phase - 2

        for y in range(self.height):
            for x in range(self.width):
                rx = max(0, min(self.width - 1, x + offset)) if split_active else x
                bx = max(0, min(self.width - 1, x - offset)) if split_active else x

                if hue_active:
                    if split_active:
                        rr, rg, rb = src[y][rx]
                        gr, gg, gb = src[y][x]
                        br, bg, bb = src[y][bx]
                        if phase < 1:
                            r = int(rr * (1-t) + rg * t)
                            g = int(gg * (1-t) + gb * t)
                            b = int(bb * (1-t) + br * t)
                        elif phase < 2:
                            r = int(rg * (1-t) + rb * t)
                            g = int(gb * (1-t) + gr * t)
                            b = int(br * (1-t) + bg * t)
                        else:
                            r = int(rb * (1-t) + rr * t)
                            g = int(gr * (1-t) + gg * t)
                            b = int(bg * (1-t) + bb * t)
                    else:
                        sr, sg, sb = src[y][x]
                        if phase < 1:
                            r = int(sr * (1-t) + sg * t)
                            g = int(sg * (1-t) + sb * t)
                            b = int(sb * (1-t) + sr * t)
                        elif phase < 2:
                            r = int(sg * (1-t) + sb * t)
                            g = int(sb * (1-t) + sr * t)
                            b = int(sr * (1-t) + sg * t)
                        else:
                            r = int(sb * (1-t) + sr * t)
                            g = int(sr * (1-t) + sg * t)
                            b = int(sg * (1-t) + sb * t)
                elif split_active:
                    r = src[y][rx][0]
                    g = src[y][x][1]
                    b = src[y][bx][2]
                else:
                    r, g, b = src[y][x]

                if brighten_active:
                    r = min(255, int(r * mult))
                    g = min(255, int(g * mult))
                    b = min(255, int(b * mult))
                display.set_pixel(x, y, (r, g, b))

    def _zoom(self, display, amount):
        if amount <= .001:
            return
        self._spatial(display, amount, 0, 0)

    def _shift(self, display, dx, dy):
        if dx == 0 and dy == 0:
            return
        self._spatial(display, 0.0, dx, dy)

    def _hue(self, display, degrees):
        self._color_pipeline(display, degrees, 0.0, 0.0)

    def _brighten(self, display, amount):
        self._color_pipeline(display, 0.0, 0.0, amount)

    def _flash(self, display, amount):
        amount = clamp01(amount)
        if amount <= .001:
            return
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = display.get_pixel(x, y)
                display.set_pixel(x, y, (int(r + (255-r)*amount), int(g + (255-g)*amount), int(b + (255-b)*amount)))

    def _sparkles(self, display, amount, seed):
        if amount <= .02:
            return
        rng = random.Random(seed)
        count = int(1 + amount * 55)
        for _ in range(count):
            x = rng.randrange(self.width)
            y = rng.randrange(self.height)
            v = rng.randint(145, 255)
            display.set_pixel(x, y, (v, v, v))

    def _rgb_split(self, display, amount):
        self._color_pipeline(display, 0.0, amount, 0.0)
