"""Memory-conscious media helpers for CircuitPython/MatrixPortal S3.

Desktop ``image_assets.py`` is intentionally not imported here. CircuitPython's
``gifio.OnDiskGif`` keeps only one decoded frame in memory. Front and back use
independent decoder/file objects and cooperative deadlines so the main runtime
never intentionally performs two GIF decodes in the same loop iteration.
"""

import time


class OnDiskGifPlayer:
    """Stream one native-size GIF from storage into a logical panel."""

    def __init__(self, path=None):
        self.path = None
        self.gif = None
        self.next_frame_at = 0.0
        self.current_delay = 0.1
        self.frames_advanced = 0
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

    @property
    def due_at(self):
        return self.next_frame_at if self.gif is not None else float("inf")

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
        self.frames_advanced = 1
        return self

    @staticmethod
    def _safe_delay(value):
        try:
            return max(0.01, float(value))
        except (TypeError, ValueError):
            return 0.1

    def is_due(self, now=None):
        if self.gif is None:
            return False
        now = time.monotonic() if now is None else float(now)
        return now >= self.next_frame_at

    def advance_if_due(self, now=None):
        """Decode at most one frame. Returns True only when a frame changed."""
        if self.gif is None:
            return False
        now = time.monotonic() if now is None else float(now)
        if now < self.next_frame_at:
            return False

        self.current_delay = self._safe_delay(self.gif.next_frame())
        self.frames_advanced += 1
        # Schedule from completion/current time instead of trying to catch up.
        # A slow decode therefore drops timing debt rather than causing bursts.
        self.next_frame_at = time.monotonic() + self.current_delay
        return True

    # Backward-compatible name for callers that do not need scheduler semantics.
    def advance(self, now=None):
        return self.advance_if_due(now)

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
        self.advance_if_due(now)
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
        self.frames_advanced = 0


class DualGifPlayers:
    """Independent front/back streaming GIF players with decode staggering.

    Each side owns its own ``gifio.OnDiskGif`` (and therefore its own file
    position). ``advance`` intentionally services at most one due decoder by
    default. The render/control loop can call it every iteration, keeping both
    timelines current without stacking two synchronous flash decodes together.
    """

    def __init__(self):
        self.players = {
            "front": OnDiskGifPlayer(),
            "back": OnDiskGifPlayer(),
        }
        self._tie_side = "front"

    def set_path(self, side, path):
        self.players[side].open(path)

    def next_due_at(self):
        front = self.players["front"].due_at
        back = self.players["back"].due_at
        return front if front <= back else back

    def advance(self, now=None, max_decodes=1):
        now = time.monotonic() if now is None else float(now)
        budget = max(0, int(max_decodes))
        changed = False

        while budget:
            front = self.players["front"]
            back = self.players["back"]
            front_due = front.is_due(now)
            back_due = back.is_due(now)
            if not front_due and not back_due:
                break

            if front_due and back_due:
                if front.due_at < back.due_at:
                    side = "front"
                elif back.due_at < front.due_at:
                    side = "back"
                else:
                    side = self._tie_side
                    self._tie_side = "back" if side == "front" else "front"
            else:
                side = "front" if front_due else "back"

            changed = self.players[side].advance_if_due(now) or changed
            budget -= 1
            # Decoding is synchronous inside gifio. Refresh ``now`` after it so
            # the scheduler never acts on a stale timestamp.
            now = time.monotonic()

        return changed

    def render(self, displays):
        for side, player in self.players.items():
            player.render(displays[side])

    def close(self):
        for player in self.players.values():
            player.close()
