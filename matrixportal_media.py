"""Memory-conscious media helpers for CircuitPython/MatrixPortal.

Desktop ``image_assets.py`` is intentionally not imported here. CircuitPython's
``gifio.OnDiskGif`` keeps only one decoded frame in memory, which is the right
model for the physical totem.
"""

import time


class OnDiskGifPlayer:
    """Stream one GIF from storage and render it into a logical panel.

    Source GIFs should already be prepared at the panel's native 64x32 size.
    The player advances only when the GIF delay expires, but the current frame
    can be re-blitted every render pass so downstream effects always start from
    a clean base image.
    """

    def __init__(self, path=None):
        self.path = None
        self.gif = None
        self.next_frame_at = 0.0
        self.current_delay = 0.1
        if path:
            self.open(path)

    @property
    def active(self):
        return self.gif is not None

    @property
    def width(self):
        return int(self.gif.width) if self.gif is not None else 0

    @property
    def height(self):
        return int(self.gif.height) if self.gif is not None else 0

    def open(self, path):
        self.close()
        try:
            import gifio
        except ImportError as exc:
            raise RuntimeError("OnDiskGifPlayer requires CircuitPython gifio") from exc

        self.path = str(path)
        self.gif = gifio.OnDiskGif(self.path)
        now = time.monotonic()
        self.current_delay = self._safe_delay(self.gif.next_frame())
        self.next_frame_at = now + self.current_delay
        return self

    @staticmethod
    def _safe_delay(value):
        try:
            return max(0.01, float(value))
        except (TypeError, ValueError):
            return 0.1

    def advance(self, now=None):
        """Advance to the next GIF frame when due. Returns True on change."""
        if self.gif is None:
            return False
        now = time.monotonic() if now is None else float(now)
        if now < self.next_frame_at:
            return False

        self.current_delay = self._safe_delay(self.gif.next_frame())
        # Schedule from *now* rather than repeatedly catching up. On a loaded
        # microcontroller this avoids a burst of decoder work after one slow frame.
        self.next_frame_at = now + self.current_delay
        return True

    def render(self, panel):
        if self.gif is None:
            panel.clear()
            return
        blit = getattr(panel, "blit_rgb565_swapped", None)
        if blit is None:
            raise TypeError(
                "OnDiskGifPlayer needs a panel implementing blit_rgb565_swapped()"
            )
        blit(self.gif.bitmap)

    def update_and_render(self, panel, now=None):
        self.advance(now)
        self.render(panel)

    def close(self):
        if self.gif is not None:
            try:
                self.gif.deinit()
            except Exception:
                pass
        self.gif = None
        self.path = None
        self.next_frame_at = 0.0


class DualGifPlayers:
    """Independent front/back streaming GIF players."""

    def __init__(self):
        self.players = {
            "front": OnDiskGifPlayer(),
            "back": OnDiskGifPlayer(),
        }

    def set_path(self, side, path):
        self.players[side].open(path)

    def advance(self, now=None):
        now = time.monotonic() if now is None else float(now)
        changed = False
        for player in self.players.values():
            changed = player.advance(now) or changed
        return changed

    def render(self, displays):
        for side, player in self.players.items():
            player.render(displays[side])

    def close(self):
        for player in self.players.values():
            player.close()
