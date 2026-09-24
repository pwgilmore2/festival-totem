"""CircuitPython MatrixPortal S3 display backend.

Two logical 64x32 panels share one caller-owned 128x32 RGB565 framebuffer. The
backend writes that framebuffer directly and calls ``RGBMatrix.refresh()`` once
per composed frame. ``rgbmatrix`` owns HUB75 refresh timing and native double
buffering while Python prepares the next frame cooperatively.
"""

from array import array


SIDES = ("front", "back")


def _swap16(value):
    value = int(value) & 0xFFFF
    return ((value & 0xFF) << 8) | (value >> 8)


def rgb888_to_rgb565(color):
    r, g, b = color
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rgb565_to_rgb888(value):
    value = int(value) & 0xFFFF
    r = (value >> 11) & 0x1F
    g = (value >> 5) & 0x3F
    b = value & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


class _FrozenRow:
    """Compact native-RGB565 snapshot compatible with ``pixels[y][x]``."""

    def __init__(self, values):
        self._values = array("H", values)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        for value in self._values:
            yield rgb565_to_rgb888(value)

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self._values))
            if start == 0 and stop == len(self._values) and step == 1:
                return _FrozenRow(self._values)
            return [rgb565_to_rgb888(self._values[i]) for i in range(start, stop, step)]
        return rgb565_to_rgb888(self._values[index])


class _LiveRow:
    def __init__(self, panel, y):
        self.panel = panel
        self.y = y

    def __len__(self):
        return self.panel.width

    def __iter__(self):
        for x in range(self.panel.width):
            yield self.panel.get_pixel(x, self.y)

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(self.panel.width)
            if start == 0 and stop == self.panel.width and step == 1:
                return _FrozenRow(
                    self.panel.get_pixel565(x, self.y)
                    for x in range(self.panel.width)
                )
            return [self.panel.get_pixel(x, self.y) for x in range(start, stop, step)]
        return self.panel.get_pixel(index, self.y)

    def __setitem__(self, index, color):
        self.panel.set_pixel(index, self.y, color)


class MatrixPortalPanel:
    """A logical panel view into one shared native RGB565 framebuffer."""

    def __init__(self, framebuffer, stride, x_offset, width, height, rotation=0):
        self.framebuffer = framebuffer
        self.stride = int(stride)
        self.x_offset = int(x_offset)
        self.width = int(width)
        self.height = int(height)
        self.rotation = int(rotation) % 360
        if self.rotation not in (0, 180):
            raise ValueError("Panel rotation must be 0 or 180 degrees")
        self.pixels = tuple(_LiveRow(self, y) for y in range(self.height))

    def _index(self, x, y):
        if self.rotation == 180:
            x = self.width - 1 - x
            y = self.height - 1 - y
        return y * self.stride + self.x_offset + x

    def clear(self):
        self.fill((0, 0, 0))

    def fill(self, color):
        packed = rgb888_to_rgb565(color)
        for y in range(self.height):
            for x in range(self.width):
                self.framebuffer[self._index(x, y)] = packed

    def set_pixel565(self, x, y, value):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.framebuffer[self._index(x, y)] = int(value) & 0xFFFF

    def get_pixel565(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.framebuffer[self._index(x, y)]
        return 0

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.set_pixel565(x, y, rgb888_to_rgb565(color))

    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return rgb565_to_rgb888(self.get_pixel565(x, y))
        return (0, 0, 0)

    def copy_from(self, other):
        packed = getattr(other, "get_pixel565", None)
        if packed is not None:
            for y in range(self.height):
                for x in range(self.width):
                    self.set_pixel565(x, y, packed(x, y))
            return
        for y in range(self.height):
            for x in range(self.width):
                self.set_pixel(x, y, other.get_pixel(x, y))

    def blend_from(self, other):
        for y in range(self.height):
            for x in range(self.width):
                color = other.get_pixel(x, y)
                if color != (0, 0, 0):
                    self.set_pixel(x, y, color)

    def blit_rgb565_swapped(self, source_bitmap):
        """Copy a gifio RGB565_SWAPPED bitmap into the native RGB565 buffer."""
        width = min(self.width, int(source_bitmap.width))
        height = min(self.height, int(source_bitmap.height))
        for y in range(height):
            for x in range(width):
                self.set_pixel565(x, y, _swap16(source_bitmap[x, y]))


class MatrixPortalDisplayBackend:
    """Direct framebuffer backend for two chained MatrixPortal S3 panels.

    S3 is the target hardware. ``bit_depth=4`` is the initial quality/performance
    target; it remains configurable so physical testing can compare 3/4/5 while
    monitoring FPS and free RAM. The framebuffer is always RGB565 regardless of
    panel output bit depth.
    """

    def __init__(
        self,
        width=64,
        height=32,
        bit_depth=4,
        serpentine=True,
        front_rotation=0,
        back_rotation=0,
        doublebuffer=True,
    ):
        try:
            import board
            import displayio
            import rgbmatrix
        except ImportError as exc:
            raise RuntimeError(
                "MatrixPortalDisplayBackend requires CircuitPython rgbmatrix support"
            ) from exc

        self.width = int(width)
        self.height = int(height)
        self.total_width = self.width * 2
        self.bit_depth = int(bit_depth)
        self.doublebuffer = bool(doublebuffer)

        displayio.release_displays()
        self.framebuffer = array("H", [0]) * (self.total_width * self.height)
        self.matrix = rgbmatrix.RGBMatrix(
            width=self.total_width,
            height=self.height,
            bit_depth=self.bit_depth,
            addr_pins=board.MTX_ADDRESS[:4],
            tile=1,
            serpentine=bool(serpentine),
            doublebuffer=self.doublebuffer,
            framebuffer=self.framebuffer,
            **board.MTX_COMMON,
        )

        self.displays = {
            "front": MatrixPortalPanel(
                self.framebuffer,
                self.total_width,
                0,
                self.width,
                self.height,
                rotation=front_rotation,
            ),
            "back": MatrixPortalPanel(
                self.framebuffer,
                self.total_width,
                self.width,
                self.width,
                self.height,
                rotation=back_rotation,
            ),
        }
        self.present()

    def get(self, side):
        return self.displays[side]

    def present(self):
        """Swap/transmit the completed RGB565 frame through native RGBMatrix."""
        self.matrix.refresh()

    def set_brightness(self, value):
        try:
            self.matrix.brightness = max(0.0, min(1.0, float(value)))
        except (AttributeError, TypeError, ValueError):
            pass

    def deinit(self):
        try:
            self.matrix.deinit()
        except Exception:
            pass
