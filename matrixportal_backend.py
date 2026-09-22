"""CircuitPython MatrixPortal display backend.

Two 64x32 logical displays are mapped onto one daisy-chained 128x32 RGB matrix.
The rest of the runtime can keep talking to independent ``front``/``back``
pixel surfaces through the same ``set_pixel``/``get_pixel`` API used by the
simulator.

Hardware-only imports are delayed until backend construction so desktop imports
remain safe.
"""

from array import array


SIDES = ("front", "back")


def _swap16(value):
    value = int(value) & 0xFFFF
    return ((value & 0xFF) << 8) | (value >> 8)


def rgb888_to_rgb565_swapped(color):
    r, g, b = color
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return _swap16(value)


def rgb565_swapped_to_rgb888(value):
    value = _swap16(value)
    r = (value >> 11) & 0x1F
    g = (value >> 5) & 0x3F
    b = value & 0x1F
    # Bit replication is cheap and gives a full 0..255 range.
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


class _FrozenRow:
    """Compact RGB565 snapshot row compatible with ``pixels[y][x]`` access."""

    def __init__(self, values):
        self._values = array("H", values)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        for value in self._values:
            yield rgb565_swapped_to_rgb888(value)

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self._values))
            if start == 0 and stop == len(self._values) and step == 1:
                return _FrozenRow(self._values)
            return [rgb565_swapped_to_rgb888(self._values[i]) for i in range(start, stop, step)]
        return rgb565_swapped_to_rgb888(self._values[index])


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
                return _FrozenRow(self.panel.get_pixel565(x, self.y) for x in range(self.panel.width))
            return [self.panel.get_pixel(x, self.y) for x in range(start, stop, step)]
        return self.panel.get_pixel(index, self.y)

    def __setitem__(self, index, color):
        self.panel.set_pixel(index, self.y, color)


class MatrixPortalPanel:
    """A 64x32 logical view into a shared MatrixPortal bitmap."""

    def __init__(self, bitmap, x_offset, width, height, rotation=0):
        self.bitmap = bitmap
        self.x_offset = int(x_offset)
        self.width = int(width)
        self.height = int(height)
        self.rotation = int(rotation) % 360
        if self.rotation not in (0, 180):
            raise ValueError("Panel rotation must be 0 or 180 degrees")
        self.pixels = tuple(_LiveRow(self, y) for y in range(self.height))

    def _coords(self, x, y):
        if self.rotation == 180:
            x = self.width - 1 - x
            y = self.height - 1 - y
        return self.x_offset + x, y

    def clear(self):
        self.fill((0, 0, 0))

    def fill(self, color):
        packed = rgb888_to_rgb565_swapped(color)
        for y in range(self.height):
            for x in range(self.width):
                mx, my = self._coords(x, y)
                self.bitmap[mx, my] = packed

    def set_pixel565(self, x, y, value):
        if 0 <= x < self.width and 0 <= y < self.height:
            mx, my = self._coords(x, y)
            self.bitmap[mx, my] = int(value) & 0xFFFF

    def get_pixel565(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            mx, my = self._coords(x, y)
            return self.bitmap[mx, my]
        return 0

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.set_pixel565(x, y, rgb888_to_rgb565_swapped(color))

    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return rgb565_swapped_to_rgb888(self.get_pixel565(x, y))
        return (0, 0, 0)

    def copy_from(self, other):
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
        """Copy an RGB565_SWAPPED bitmap (including gifio frames) 1:1."""
        width = min(self.width, int(source_bitmap.width))
        height = min(self.height, int(source_bitmap.height))
        for y in range(height):
            for x in range(width):
                self.set_pixel565(x, y, source_bitmap[x, y])


class MatrixPortalDisplayBackend:
    """Physical backend for two chained RGB panels on one MatrixPortal.

    ``bit_depth`` is deliberately configurable. A value of 2 is the safest
    starting point for MatrixPortal M4; S3 hardware can generally afford more.
    """

    def __init__(
        self,
        width=64,
        height=32,
        bit_depth=2,
        color_order="RGB",
        serpentine=True,
        front_rotation=0,
        back_rotation=0,
    ):
        try:
            import displayio
            from adafruit_matrixportal.matrix import Matrix
        except ImportError as exc:
            raise RuntimeError(
                "MatrixPortalDisplayBackend requires CircuitPython and the "
                "adafruit_matrixportal library"
            ) from exc

        self.width = int(width)
        self.height = int(height)
        self.total_width = self.width * 2
        self.bit_depth = int(bit_depth)

        self.matrix = Matrix(
            width=self.total_width,
            height=self.height,
            bit_depth=self.bit_depth,
            color_order=color_order,
            serpentine=bool(serpentine),
            tile_rows=1,
            rotation=0,
        )
        self.display = self.matrix.display
        self.display.auto_refresh = False

        # gifio.OnDiskGif exposes RGB565 in the byte ordering expected by
        # RGB565_SWAPPED, so this keeps GIF frame copies conversion-free.
        self.bitmap = displayio.Bitmap(self.total_width, self.height, 65536)
        converter = displayio.ColorConverter(
            input_colorspace=displayio.Colorspace.RGB565_SWAPPED
        )
        group = displayio.Group()
        group.append(displayio.TileGrid(self.bitmap, pixel_shader=converter))
        self.display.root_group = group
        self.group = group

        self.displays = {
            "front": MatrixPortalPanel(
                self.bitmap, 0, self.width, self.height, rotation=front_rotation
            ),
            "back": MatrixPortalPanel(
                self.bitmap, self.width, self.width, self.height, rotation=back_rotation
            ),
        }
        self.present()

    def get(self, side):
        return self.displays[side]

    def present(self):
        """Push the composed bitmap to the HUB75 framebuffer once per frame."""
        try:
            self.display.refresh(minimum_frames_per_second=0)
        except (TypeError, RuntimeError):
            try:
                self.display.refresh()
            except RuntimeError:
                # FramebufferDisplay can reject an early refresh; the next
                # runtime frame will try again.
                pass

    def deinit(self):
        try:
            self.display.root_group = None
        except Exception:
            pass
        deinit = getattr(self.matrix, "deinit", None)
        if deinit:
            deinit()
