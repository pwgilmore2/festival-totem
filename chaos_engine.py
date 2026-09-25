"""Stateful final-frame Chaos effects.

Chaos is an explicit runtime stage: commands update this engine's state and the
simulator calls ``apply`` after content, reactivity, overlays and scene
transitions. Importing this module has no side effects or monkeypatches.
"""

import math
import runtime_random as random
import time

from visual_engine import copy_pixels


CHILL_MODES = {"trance", "liquid", "tunnel", "warp", "prism", "rainbow"}


class ChaosEngine:
    def __init__(self, layer_engine):
        self.layer_engine = layer_engine
        self.mode = None
        self.strength = 0.0
        self.started = 0.0
        self.until = 0.0
        self.releasing = 0.0
        self.release_duration = 0.0
        self.locked = False
        self.xy = {"x": 0.5, "y": 0.5, "velocity": 0.0}

    @staticmethod
    def _clamp01(value):
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _smooth01(value):
        value = max(0.0, min(1.0, float(value)))
        return value * value * (3.0 - 2.0 * value)

    @property
    def active(self):
        return bool(self.mode)

    def snapshot(self):
        kind = "XY Pad" if self.mode == "xyintent" else self.mode
        return {"locked": self.locked, "active": self.active, "kind": kind}

    def set_locked(self, value):
        self.locked = bool(value)
        if self.locked:
            self._clear()

    def trigger(self, value):
        if self.locked or not isinstance(value, dict):
            return
        kind = str(value.get("kind", "")).lower().strip()
        if not kind:
            return
        try:
            strength = self._clamp01(value.get("strength", 1.0))
        except Exception:
            strength = 1.0
        try:
            duration = max(0.05, float(value.get("duration", 30.0)))
        except Exception:
            duration = 30.0
        now = time.monotonic()
        self.mode = kind
        self.strength = strength
        self.started = now
        self.until = now + duration
        self.releasing = 0.0
        self.release_duration = 0.0

    def update_xy(self, value):
        if self.locked or not isinstance(value, dict):
            return
        try:
            x = self._clamp01(value.get("x", 0.5))
            y = self._clamp01(value.get("y", 0.5))
            velocity = self._clamp01(value.get("velocity", 0.0))
            strength = self._clamp01(value.get("strength", 1.0))
        except Exception:
            return
        now = time.monotonic()
        if self.mode != "xyintent":
            self.started = now
        self.mode = "xyintent"
        self.strength = strength
        self.until = now + 0.35
        self.releasing = 0.0
        self.release_duration = 0.0
        self.xy = {"x": x, "y": y, "velocity": velocity}

    def stop(self):
        if not self.mode:
            return
        now = time.monotonic()
        if self.mode in CHILL_MODES:
            duration = 0.85
        elif self.mode == "meltdown":
            duration = 0.65
        elif self.mode == "xyintent":
            duration = 0.30
        else:
            self._clear()
            return
        if not self.releasing:
            self.releasing = now
            self.release_duration = duration
        self.until = 0.0

    def update(self):
        if not self.mode:
            return
        now = time.monotonic()
        if self.releasing:
            if now - self.releasing >= self.release_duration:
                self._clear()
            return
        if self.until and now > self.until:
            self.stop()

    def _clear(self):
        self.mode = None
        self.strength = 0.0
        self.until = 0.0
        self.releasing = 0.0
        self.release_duration = 0.0
        self.xy = {"x": 0.5, "y": 0.5, "velocity": 0.0}

    def _envelope(self):
        if not self.mode:
            return 0.0
        now = time.monotonic()
        elapsed = max(0.0, now - self.started)
        if self.mode == "xyintent":
            env = self._smooth01(elapsed / 0.18)
        elif self.mode in CHILL_MODES:
            env = 0.58 + 0.42 * self._smooth01(elapsed / 0.75)
        elif self.mode == "meltdown":
            env = 0.72 + 0.28 * self._smooth01(elapsed / 0.45)
        else:
            env = self._smooth01(elapsed / 0.12)
        if self.releasing:
            release = (now - self.releasing) / max(0.01, self.release_duration)
            env *= 1.0 - self._smooth01(release)
        return max(0.0, min(1.0, env))

    def apply(self, display, frame_number, signals=None):
        self.update()
        if not self.mode or self.locked:
            return
        amount = self.strength * self._envelope()
        if amount <= 0.002:
            return
        signals = signals or {}
        mode = self.mode
        layer = self.layer_engine

        if mode in ("glitch", "chaos"):
            layer.guest_burst(display, mode, amount, frame_number)
        elif mode == "rainbow":
            layer._hue(display, math.sin(frame_number * 0.022) * 150 * amount)
            layer._brighten(display, amount * 0.10)
        elif mode == "pixelmelt":
            self._pixel_melt(display, amount, frame_number)
        elif mode == "meltdown":
            self._pixel_melt(display, amount * 0.88, frame_number)
            layer._hue(display, math.sin(frame_number * 0.030) * 42 * amount)
        elif mode == "jumble":
            self._jumble(display, amount, frame_number)
        elif mode == "bassjostle":
            bass = self._clamp01(signals.get("bass", 0.0))
            hit = 1.0 if signals.get("beat") else 0.0
            power = amount * min(1.0, bass * 1.45 + hit * 0.45)
            layer._shift(display, int(math.sin(frame_number * 1.9) * power * 9), int(math.cos(frame_number * 1.45) * power * 6))
            layer._rgb_split(display, power * 0.5)
            if hit:
                layer._zoom(display, power * 0.16)
        elif mode == "trance":
            wave = 0.5 + 0.5 * math.sin(frame_number * 0.035)
            layer._zoom(display, (0.05 + wave * 0.10) * amount)
            self._row_wave(display, (0.30 + wave * 0.38) * amount, frame_number, "teal", speed=0.032)
            layer._rgb_split(display, (0.05 + wave * 0.13) * amount)
        elif mode == "liquid":
            wave = 0.5 + 0.5 * math.sin(frame_number * 0.030)
            self._row_wave(display, (0.28 + wave * 0.38) * amount, frame_number, speed=0.028, frequency=0.31)
            layer._hue(display, math.sin(frame_number * 0.024) * 72 * amount)
        elif mode == "warp":
            wave = 0.5 + 0.5 * math.sin(frame_number * 0.030)
            layer._zoom(display, (0.065 + wave * 0.17) * amount)
            layer._shift(display, int(math.sin(frame_number * 0.045) * amount * 3), int(math.cos(frame_number * 0.036) * amount * 2))
            layer._hue(display, math.sin(frame_number * 0.020) * 95 * amount)
        elif mode == "prism":
            wave = 0.5 + 0.5 * math.sin(frame_number * 0.032)
            layer._rgb_split(display, (0.14 + wave * 0.46) * amount)
            layer._hue(display, math.sin(frame_number * 0.022) * 80 * amount)
            layer._sparkles(display, amount * 0.16, frame_number * 9)
        elif mode == "tunnel":
            wave = 0.5 + 0.5 * math.sin(frame_number * 0.035)
            layer._zoom(display, (0.075 + 0.23 * wave) * amount)
            layer._rgb_split(display, (0.055 + 0.18 * (1 - wave)) * amount)
            layer._hue(display, math.sin(frame_number * 0.020) * 100 * amount)
        elif mode == "xyintent":
            self._apply_xy(display, amount, frame_number)
        else:
            layer.guest_burst(display, mode, amount, frame_number)

    def _row_wave(self, display, amount, frame, tint=None, speed=0.035, frequency=0.34):
        src = copy_pixels(display)
        amp = max(1, int(1 + amount * 5))
        for y in range(display.height):
            shift = int(math.sin(y * frequency + frame * speed) * amp)
            for x in range(display.width):
                sx = max(0, min(display.width - 1, x - shift))
                r, g, b = src[y][sx]
                if tint == "teal":
                    r = int(r * 0.44)
                    g = min(255, int(g * 1.04 + b * 0.15))
                    b = min(255, int(b * 1.10 + g * 0.05))
                display.set_pixel(x, y, (r, g, b))

    def _pixel_melt(self, display, amount, frame):
        src = copy_pixels(display)
        elapsed = max(0.0, time.monotonic() - self.started)
        strength = min(1.0, elapsed * 0.30) * amount
        rng = random.Random(4107)
        for x in range(display.width):
            speed = 0.35 + rng.random() * 0.9
            drop = int(strength * speed * (display.height + 6))
            wobble = int(math.sin(frame * 0.055 + x * 0.7) * amount)
            for y in range(display.height):
                sy = y - drop - wobble
                sy = max(0, min(display.height - 1, sy))
                display.set_pixel(x, y, src[sy][x])

    def _jumble(self, display, amount, frame):
        src = copy_pixels(display)
        block = 4
        cols = max(1, display.width // block)
        rows = max(1, display.height // block)
        rng = random.Random((frame // 5) + 7301)
        swaps = int(2 + amount * cols * rows * 0.45)
        mapping = list(range(cols * rows))
        for _ in range(swaps):
            a = rng.randrange(len(mapping))
            b = rng.randrange(len(mapping))
            mapping[a], mapping[b] = mapping[b], mapping[a]
        for by in range(rows):
            for bx in range(cols):
                src_index = mapping[by * cols + bx]
                sx0 = (src_index % cols) * block
                sy0 = (src_index // cols) * block
                for oy in range(block):
                    for ox in range(block):
                        x = bx * block + ox
                        y = by * block + oy
                        if x < display.width and y < display.height:
                            display.set_pixel(x, y, src[min(display.height - 1, sy0 + oy)][min(display.width - 1, sx0 + ox)])

    def _apply_xy(self, display, amount, frame_number):
        x = self._clamp01(self.xy.get("x", 0.5))
        y = self._clamp01(self.xy.get("y", 0.5))
        dead = 0.10
        left = max(0.0, (-((x - 0.5)) - dead) / (0.5 - dead))
        right = max(0.0, ((x - 0.5) - dead) / (0.5 - dead))
        up = max(0.0, (-((y - 0.5)) - dead) / (0.5 - dead))
        down = max(0.0, ((y - 0.5) - dead) / (0.5 - dead))
        layer = self.layer_engine
        if up > 0:
            layer._zoom(display, up * amount * 0.28)
        if down > 0:
            layer._shift(display, int(math.sin(frame_number * 1.7) * down * amount * 6), int(math.cos(frame_number * 1.35) * down * amount * 4))
        if right > 0:
            layer._rgb_split(display, right * amount * 0.85)
        if left > 0:
            layer._rgb_split(display, left * amount * 0.32)
            layer._shift(display, int(math.sin(frame_number * 2.5) * left * amount * 7), 0)
