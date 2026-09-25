"""CircuitPython MatrixPortal S3 display backend.

Two logical 64x32 panels share a displayio-owned 128x32 RGB565 Bitmap.
The prior caller-owned rgbmatrix framebuffer hard-faulted on the physical S3;
Bitmap plus FramebufferDisplay rendered cleanly with over 2 MB free.
"""

from array import array


SIDES = ("front", "back")


class _BitmapLinearBuffer:
    """Expose Bitmap pixels through the renderer's linear RGB565 indexing."""

    def __init__(self, bitmap, stride, swapped_storage=False):
        self.bitmap = bitmap
        self.stride = int(stride)
        self.swapped_storage = bool(swapped_storage)

    def __getitem__(self, index):
        index = int(index)
        value = self.bitmap[index % self.stride, index // self.stride]
        return _swap16(value) if self.swapped_storage else value

    def __setitem__(self, index, value):
        index = int(index)
        value = int(value) & 0xFFFF
        self.bitmap[index % self.stride, index // self.stride] = (
            _swap16(value) if self.swapped_storage else value
        )


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

    snapshot_on_demand = True

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

    def dim(self, brightness):
        """Dim RGB565 in place without converting each pixel to an RGB tuple."""
        scale = max(0, min(256, int(float(brightness) * 256)))
        bitmap = self.framebuffer.bitmap
        swapped = self.framebuffer.swapped_storage
        for y in range(self.height):
            for x in range(self.width):
                px = self.width - 1 - x if self.rotation == 180 else x
                py = self.height - 1 - y if self.rotation == 180 else y
                bx = self.x_offset + px
                value = bitmap[bx, py]
                if swapped:
                    value = _swap16(value)
                value = (((((value >> 11) & 31) * scale >> 8) << 11)
                         | (((((value >> 5) & 63) * scale >> 8) << 5))
                         | ((value & 31) * scale >> 8))
                bitmap[bx, py] = _swap16(value) if swapped else value

    def fill(self, color):
        packed = rgb888_to_rgb565(color)
        import bitmaptools
        native_fill = getattr(bitmaptools, "fill_region", None)
        if native_fill is not None:
            value = _swap16(packed) if self.framebuffer.swapped_storage else packed
            native_fill(self.framebuffer.bitmap, self.x_offset, 0,
                        self.x_offset + self.width, self.height, value)
            return
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
        if (self.rotation == 0 and getattr(other, "rotation", None) == 0
                and getattr(other, "framebuffer", None) is self.framebuffer):
            import bitmaptools
            bitmaptools.blit(self.framebuffer.bitmap, self.framebuffer.bitmap,
                             self.x_offset, 0,
                             x1=other.x_offset, y1=0,
                             x2=other.x_offset + min(self.width, other.width),
                             y2=min(self.height, other.height))
            return
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
        if self.rotation == 0 and self.framebuffer.swapped_storage:
            # gifio's Bitmap already stores RGB565_SWAPPED. Native C blit
            # moves the whole frame without 2048 Python pixel assignments.
            import bitmaptools
            bitmaptools.blit(self.framebuffer.bitmap, source_bitmap, self.x_offset, 0)
            return
        width = min(self.width, int(source_bitmap.width))
        height = min(self.height, int(source_bitmap.height))
        for y in range(height):
            for x in range(width):
                self.set_pixel565(x, y, _swap16(source_bitmap[x, y]))

    def blit_icon(self, asset, x, y):
        """Cache an icon as RGB565 and draw its opaque pixels in native code."""
        if self.rotation != 0:
            return False
        import bitmaptools
        import displayio
        bitmap = getattr(asset, "_board_bitmap", None)
        if bitmap is None:
            rows = asset.pixels
            height = len(rows)
            width = len(rows[0]) if height else 0
            if not width:
                return True
            bitmap = displayio.Bitmap(width, height, 65536)
            # Reserve one RGB565 value for transparency. If an opaque icon
            # pixel matches it, choose the adjacent near-black value.
            for py, row in enumerate(rows):
                for px, (r, g, b, alpha) in enumerate(row):
                    color = rgb888_to_rgb565((r, g, b)) if alpha else 1
                    if alpha and color == 1:
                        color = 2
                    bitmap[px, py] = _swap16(color) if self.framebuffer.swapped_storage else color
            asset._board_bitmap = bitmap
        x1, y1 = max(0, -x), max(0, -y)
        x2 = min(bitmap.width, self.width - x)
        y2 = min(bitmap.height, self.height - y)
        if x2 > x1 and y2 > y1:
            skip = 0x0100 if self.framebuffer.swapped_storage else 1
            bitmaptools.blit(self.framebuffer.bitmap, bitmap,
                             self.x_offset + x + x1, y + y1,
                             x1=x1, y1=y1, x2=x2, y2=y2,
                             skip_source_index=skip)
        return True


class MatrixPortalDisplayBackend:
    """Direct framebuffer backend for two chained MatrixPortal S3 panels.

    The known-working physical baseline uses bit depth 1 and no doublebuffer.
    Both parameters remain configurable for later controlled measurements.
    """

    def __init__(
        self,
        width=64,
        height=32,
        bit_depth=1,
        serpentine=True,
        front_rotation=0,
        back_rotation=0,
        doublebuffer=False,
        swapped_storage=False,
    ):
        try:
            import board
            import displayio
            import framebufferio
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
        self.swapped_storage = bool(swapped_storage)

        displayio.release_displays()
        # Physical panels show RBG when RGB is requested. Correct the wiring
        # order once at the matrix driver instead of swapping every pixel.
        common_pins = dict(board.MTX_COMMON)
        rgb_pins = tuple(common_pins["rgb_pins"])
        if len(rgb_pins) != 6:
            raise ValueError("Expected six MatrixPortal RGB pins")
        common_pins["rgb_pins"] = (
            rgb_pins[0], rgb_pins[2], rgb_pins[1],
            rgb_pins[3], rgb_pins[5], rgb_pins[4],
        )
        self.matrix = rgbmatrix.RGBMatrix(
            width=self.total_width,
            height=self.height,
            bit_depth=self.bit_depth,
            addr_pins=board.MTX_ADDRESS[:4],
            tile=1,
            serpentine=bool(serpentine),
            doublebuffer=self.doublebuffer,
            **common_pins,
        )
        self.display = framebufferio.FramebufferDisplay(self.matrix, auto_refresh=False)
        self.bitmap = displayio.Bitmap(self.total_width, self.height, 65536)
        colorspace = (displayio.Colorspace.RGB565_SWAPPED if self.swapped_storage
                      else displayio.Colorspace.RGB565)
        shader = displayio.ColorConverter(input_colorspace=colorspace)
        root = displayio.Group()
        root.append(displayio.TileGrid(self.bitmap, pixel_shader=shader))
        self.display.root_group = root
        self.framebuffer = _BitmapLinearBuffer(self.bitmap, self.total_width,
                                                self.swapped_storage)

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
        """Render the RGB565 Bitmap using the working displayio path."""
        self.display.refresh()

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
