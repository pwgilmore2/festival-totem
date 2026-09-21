"""Runtime-facing IO seams for simulator and future physical hardware.

Keep visual/controller code talking to stable display and signal shapes while the
actual source (pygame/phone today, MatrixPortal + sensors later) can change.
"""

import time

from display import VirtualDisplay


SIDES = ("front", "back")
AUDIO_KEYS = ("volume", "bass", "mids", "highs", "beat")


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


class VirtualDisplayBackend:
    """Current simulator display backend.

    A physical backend only needs to expose the same ``displays`` mapping with
    front/back display objects implementing the existing pixel API.
    """

    def __init__(self, width, height):
        self.width = int(width)
        self.height = int(height)
        self.displays = {side: VirtualDisplay(self.width, self.height) for side in SIDES}

    def get(self, side):
        return self.displays[side]


class SignalStore:
    """Stable normalized signal interface shared by phone and future sensors.

    Phone audio/motion can feed this today. A physical runtime can update the
    exact same store from an I2S microphone and LIS3DH without changing effects.
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


class HardwareDisplayBackend:
    """Placeholder contract for the MatrixPortal implementation.

    Intentionally raises until the board arrives; importing simulator code never
    touches hardware-specific libraries.
    """

    def __init__(self, width, height):
        raise NotImplementedError("MatrixPortal display backend not installed yet")


class HardwareSignalSource:
    """Future I2S microphone + LIS3DH source contract.

    Physical code will call ``SignalStore.update_audio`` and ``update_motion``
    with the same normalized values the simulator already consumes.
    """

    def __init__(self, store):
        self.store = store

    def poll(self):
        raise NotImplementedError("Hardware sensors not installed yet")
