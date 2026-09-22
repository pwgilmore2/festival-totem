"""Runtime-facing IO seams for simulator and physical hardware.

Visual/controller code talks to the same front/back display and normalized signal
interfaces. Hardware-specific imports stay lazy so the desktop simulator never
loads CircuitPython-only modules.
"""

import time

from display import VirtualDisplay


SIDES = ("front", "back")
AUDIO_KEYS = ("volume", "bass", "mids", "highs", "beat")


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


class VirtualDisplayBackend:
    """Desktop simulator display backend."""

    def __init__(self, width, height):
        self.width = int(width)
        self.height = int(height)
        self.displays = {side: VirtualDisplay(self.width, self.height) for side in SIDES}

    def get(self, side):
        return self.displays[side]

    def present(self):
        """Simulator pixels are already consumed directly by Pygame."""
        return None

    def deinit(self):
        return None


class HardwareDisplayBackend:
    """Lazy MatrixPortal backend adapter.

    Constructing this class on CircuitPython creates one chained 128x32 matrix
    and exposes two independent logical 64x32 displays. Importing this module on
    desktop remains safe because MatrixPortal libraries are loaded only here.
    """

    def __init__(self, width=64, height=32, **kwargs):
        from matrixportal_backend import MatrixPortalDisplayBackend

        self._backend = MatrixPortalDisplayBackend(width, height, **kwargs)
        self.width = self._backend.width
        self.height = self._backend.height
        self.displays = self._backend.displays

    def get(self, side):
        return self.displays[side]

    def present(self):
        return self._backend.present()

    def deinit(self):
        return self._backend.deinit()


class SignalStore:
    """Stable normalized signal interface shared by phone and future sensors.

    Phone audio/motion can feed this today. A physical runtime can update the
    exact same store from a microphone or accelerometer without changing visual
    effect code.
    """

    def __init__(self, audio_timeout=1.0):
        self.audio_timeout = float(audio_timeout)
        self.audio = {
            "volume": 0.0,
            "bass": 0.0,
            "mids": 0.0,
            "highs": 0.0,
            "beat": False,
            "last_update": 0.0,
        }
        self.motion = {
            "tilt_x": 0.0,
            "tilt_y": 0.0,
            "shake": 0.0,
            "tap": False,
        }

    def audio_fresh(self):
        return time.monotonic() - self.audio["last_update"] < self.audio_timeout

    def update_audio(self, value):
        if not isinstance(value, dict):
            return
        for key in ("volume", "bass", "mids", "highs"):
            if key in value:
                try:
                    self.audio[key] = _clamp01(value[key])
                except (TypeError, ValueError):
                    pass
        self.audio["beat"] = bool(value.get("beat", False))
        self.audio["last_update"] = time.monotonic()

    def update_motion(self, value):
        if not isinstance(value, dict):
            return
        for key in ("tilt_x", "tilt_y"):
            if key in value:
                try:
                    self.motion[key] = max(-1.0, min(1.0, float(value[key])))
                except (TypeError, ValueError):
                    pass
        if "shake" in value:
            try:
                self.motion["shake"] = _clamp01(value["shake"])
            except (TypeError, ValueError):
                pass
        self.motion["tap"] = bool(value.get("tap", False))

    def snapshot(self):
        out = {
            "volume": 0.0,
            "bass": 0.0,
            "mids": 0.0,
            "highs": 0.0,
            "beat": False,
            **self.motion,
        }
        if self.audio_fresh():
            out.update({key: self.audio[key] for key in AUDIO_KEYS})
        return out

    def end_frame(self):
        # Tap is one-frame; shake naturally decays until a physical source replaces it.
        self.motion["tap"] = False
        self.motion["shake"] *= 0.90


class HardwareSignalSource:
    """Sensor-source contract for a future on-device microphone/accelerometer."""

    def __init__(self, store):
        self.store = store

    def poll(self):
        raise NotImplementedError("Hardware sensors not installed yet")
