"""Native transition engine for content and full-scene compositor stages.

The simulator owns transition scope explicitly. This module only implements
transition timing and pixels; importing it has no side effects or monkeypatches.
"""

import math
import runtime_random as random

from visual_engine import TransitionManager as BaseTransitionManager
from visual_engine import blend_color, clamp01, copy_pixels, write_pixels


INTENSE_TRANSITIONS = ("Morph", "Spin", "Rip", "Slam", "Bounce", "Shatter", "Vortex", "Implode")


def _ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def _sample(pixels, x, y, width, height, fallback=(0, 0, 0)):
    xi = int(round(x))
    yi = int(round(y))
    if 0 <= xi < width and 0 <= yi < height:
        return pixels[yi][xi]
    return fallback


class TransitionManager(BaseTransitionManager):
    """Transition manager with native support for the full-scene family.

    It intentionally owns ``update`` so transition timing cannot be altered by
    unrelated performance/Chaos modules.
    """

    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False
            self.source = None
            self._intense_target = None

    def begin(self, display, kind="Fade", duration=0.8, source=None):
        if kind not in INTENSE_TRANSITIONS:
            super().begin(display, kind, duration)
        else:
            self.kind = kind
            self.duration = max(0.18, min(5.0, float(duration)))
            self.elapsed = 0.0
            self.source = copy_pixels(display)
            self.seed = random.randrange(1_000_000)
            self.active = True

        if self.active and source is not None:
            self.source = [row[:] for row in source]

        self._intense_target = None
        self._morph_pairs = None
        self._morph_native = None
        self._shatter_tiles = None

    def apply(self, display):
        if self.kind not in INTENSE_TRANSITIONS:
            return super().apply(display)
        if not self.active or self.source is None:
            return
        if self._intense_target is None:
            self._intense_target = copy_pixels(display)
        target = self._intense_target
        p = self.progress
        if self.kind == "Morph":
            native = getattr(display, "native_scene_morph", None)
            if native is not None:
                self._morph_native = native(self.source, target, p, self.seed,
                                            self._morph_native)
                if self._morph_native is not None:
                    return
            self._morph(display, target, p)
        elif self.kind == "Spin":
            self._spin(display, target, p)
        elif self.kind == "Rip":
            self._rip(display, target, p)
        elif self.kind == "Slam":
            self._slam(display, target, p)
        elif self.kind == "Bounce":
            self._bounce(display, target, p)
        elif self.kind == "Shatter":
            self._shatter(display, target, p)
        elif self.kind == "Vortex":
            self._vortex(display, target, p)
        elif self.kind == "Implode":
            self._implode(display, target, p)

    def _morph(self, display, target, p):
        if self._morph_pairs is None:
            src_coords = [(x, y) for y in range(self.height) for x in range(self.width)]
            dst_coords = list(src_coords)

            def key_src(pt):
                x, y = pt
                r, g, b = self.source[y][x]
                return (r + g + b, max(r, g, b) - min(r, g, b), y, x)

            def key_dst(pt):
                x, y = pt
                r, g, b = target[y][x]
                return (r + g + b, max(r, g, b) - min(r, g, b), y, x)

            src_coords.sort(key=key_src)
            dst_coords.sort(key=key_dst)
            self._morph_pairs = list(zip(src_coords, dst_coords))

        for y in range(self.height):
            for x in range(self.width):
                tr, tg, tb = target[y][x]
                bg = p * p * 0.32
                display.set_pixel(x, y, (int(tr * bg), int(tg * bg), int(tb * bg)))

        arc = math.sin(math.pi * p)
        for i, ((sx, sy), (dx, dy)) in enumerate(self._morph_pairs):
            sr, sg, sb = self.source[sy][sx]
            dr, dg, db = target[dy][dx]
            if max(sr, sg, sb, dr, dg, db) < 18 and p < .78:
                continue
            wobble = math.sin((i * .73) + self.seed * .001) * arc * 2.4
            mx = sx + (dx - sx) * p + wobble
            my = sy + (dy - sy) * p + math.cos((i * .51) + self.seed * .002) * arc * 1.5
            color = blend_color((sr, sg, sb), (dr, dg, db), p)
            xi = int(round(mx))
            yi = int(round(my))
            if 0 <= xi < self.width and 0 <= yi < self.height:
                display.set_pixel(xi, yi, color)

        if p > .82:
            mix = (p - .82) / .18
            for y in range(self.height):
                for x in range(self.width):
                    display.set_pixel(x, y, blend_color(display.get_pixel(x, y), target[y][x], mix))

    def _spin(self, display, target, p):
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0
        for y in range(self.height):
            for x in range(self.width):
                dx = x - cx
                dy = y - cy
                if p < .5:
                    local = p * 2.0
                    angle = -local * math.pi * 1.45
                    scale = max(.08, 1.0 - local * .92)
                    src = self.source
                else:
                    local = (p - .5) * 2.0
                    angle = (1.0 - local) * math.pi * 1.45
                    scale = max(.08, .08 + local * .92)
                    src = target
                ca = math.cos(angle)
                sa = math.sin(angle)
                rx = (dx * ca + dy * sa) / scale
                ry = (-dx * sa + dy * ca) / scale
                display.set_pixel(x, y, _sample(src, cx + rx, cy + ry, self.width, self.height))

    def _rip(self, display, target, p):
        rng = random.Random(self.seed)
        jag = [rng.randint(-5, 5) + int(math.sin(y * .7 + self.seed) * 2) for y in range(self.height)]
        edge = -8 + p * (self.width + 16)
        for y in range(self.height):
            tear = edge + jag[y]
            for x in range(self.width):
                d = x - tear
                if d < -2:
                    c = target[y][x]
                elif d > 3:
                    c = self.source[y][x]
                elif abs(d) < 1.2:
                    c = (255, 245, 220)
                elif d < 0:
                    c = _sample(target, x - 2, y, self.width, self.height)
                else:
                    c = _sample(self.source, x + 2, y, self.width, self.height)
                display.set_pixel(x, y, c)

    def _slam(self, display, target, p):
        e = _ease_out_back(p)
        offset = int(round((1.0 - e) * -(self.height + 5)))
        shake = int(round(math.sin(p * math.pi * 9) * (1.0 - p) * 3.5)) if p > .45 else 0
        for y in range(self.height):
            for x in range(self.width):
                ty = y - offset - shake
                if 0 <= ty < self.height:
                    c = target[ty][x]
                else:
                    sy = y + int(p * (self.height + 3))
                    c = _sample(self.source, x, sy, self.width, self.height)
                display.set_pixel(x, y, c)

    def _bounce(self, display, target, p):
        travel = (1.0 - p) * self.width
        bounce = math.sin(p * math.pi * 5.0) * (1.0 - p) * 7.0
        offset = int(round(travel + bounce))
        for y in range(self.height):
            for x in range(self.width):
                tx = x - offset
                if 0 <= tx < self.width:
                    c = target[y][tx]
                else:
                    sx = x + int(p * self.width)
                    c = _sample(self.source, sx, y, self.width, self.height)
                display.set_pixel(x, y, c)

    def _shatter(self, display, target, p):
        tile = 8
        cols = (self.width + tile - 1) // tile
        rows = (self.height + tile - 1) // tile
        if self._shatter_tiles is None:
            rng = random.Random(self.seed)
            data = []
            cx = (self.width - 1) / 2.0
            cy = (self.height - 1) / 2.0
            for gy in range(rows):
                for gx in range(cols):
                    tcx = gx * tile + tile / 2
                    tcy = gy * tile + tile / 2
                    vx = tcx - cx + rng.uniform(-8, 8)
                    vy = tcy - cy + rng.uniform(-5, 5)
                    mag = max(1.0, math.sqrt(vx * vx + vy * vy))
                    speed = rng.uniform(11, 24)
                    data.append((gx, gy, vx / mag * speed, vy / mag * speed, rng.uniform(-.8, .8)))
            self._shatter_tiles = data

        write_pixels(display, target)
        fade = max(0.0, 1.0 - p * 1.18)
        for gx, gy, vx, vy, spin in self._shatter_tiles:
            ox = int(vx * (p ** 1.35))
            oy = int(vy * (p ** 1.35) + 10 * p * p)
            for ly in range(tile):
                for lx in range(tile):
                    sx = gx * tile + lx
                    sy = gy * tile + ly
                    if sx >= self.width or sy >= self.height:
                        continue
                    dx = sx + ox
                    dy = sy + oy
                    if 0 <= dx < self.width and 0 <= dy < self.height:
                        c = self.source[sy][sx]
                        display.set_pixel(dx, dy, tuple(int(v * fade) for v in c))

    def _vortex(self, display, target, p):
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0
        for y in range(self.height):
            for x in range(self.width):
                dx = x - cx
                dy = y - cy
                r = math.sqrt(dx * dx + dy * dy)
                if p < .5:
                    local = p * 2
                    twist = local * (2.8 + (1 - min(1, r / max(self.width, self.height))) * 4.2)
                    scale = max(.08, 1.0 - local * .92)
                    src = self.source
                else:
                    local = (p - .5) * 2
                    twist = -(1 - local) * (2.8 + (1 - min(1, r / max(self.width, self.height))) * 4.2)
                    scale = max(.08, .08 + local * .92)
                    src = target
                a = math.atan2(dy, dx) + twist
                rr = r / scale
                display.set_pixel(x, y, _sample(src, cx + math.cos(a) * rr, cy + math.sin(a) * rr, self.width, self.height))

    def _implode(self, display, target, p):
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0
        if p < .52:
            local = p / .52
            radius = max(self.width, self.height) * (1.0 - local) * .65
            for y in range(self.height):
                for x in range(self.width):
                    dx = x - cx
                    dy = y - cy
                    d = math.sqrt(dx * dx + dy * dy)
                    scale = max(.04, 1.0 - local * .96)
                    c = _sample(self.source, cx + dx / scale, cy + dy / scale, self.width, self.height)
                    dim = max(0.0, 1.0 - local * .75)
                    display.set_pixel(x, y, tuple(int(v * dim) for v in c) if d < radius + 6 else (0, 0, 0))
        else:
            local = (p - .52) / .48
            scale = max(.05, .05 + local * .95)
            for y in range(self.height):
                for x in range(self.width):
                    dx = x - cx
                    dy = y - cy
                    display.set_pixel(x, y, _sample(target, cx + dx / scale, cy + dy / scale, self.width, self.height))
