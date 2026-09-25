"""Desktop regression test for the two-panel MatrixPortal mapping."""

import sys
import types
import unittest
from array import array
from unittest.mock import patch

from matrixportal_backend import MatrixPortalDisplayBackend, MatrixPortalPanel, _BitmapLinearBuffer, rgb888_to_rgb565
from display import VirtualDisplay
from visual_engine import VisualLayerEngine


class FakeRGBMatrix:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.refresh_count = 0

    def refresh(self):
        self.refresh_count += 1

    def deinit(self):
        pass


class FakeBitmap:
    def __init__(self, width, height, value_count):
        self.data = [0] * (width * height)
        self.width = width
        self.height = height

    def __getitem__(self, xy):
        x, y = xy
        return self.data[y * self.width + x]

    def __setitem__(self, xy, value):
        x, y = xy
        self.data[y * self.width + x] = value

    def fill(self, value):
        self.data[:] = [value] * len(self.data)


class FakeFrameBufferDisplay:
    def __init__(self, matrix, auto_refresh=False):
        self.matrix = matrix
        self.root_group = None

    def refresh(self):
        self.matrix.refresh()


class MatrixPortalBackendTests(unittest.TestCase):
    def test_vector_colors_preserve_chaos_pipeline_and_other_face(self):
        try:
            import numpy
        except ImportError:
            self.skipTest("desktop numpy is unavailable")
        from matrixportal_ulab_colors import apply

        class BufferedBitmap(array):
            width = 128
            height = 32

            def __new__(cls):
                return array.__new__(cls, "H", [0] * (128 * 32))

        for degrees, split, bright in ((0, .5, 0), (75, 0, 0),
                                       (170, .4, .1), (239, 0, 0),
                                       (359, .8, .4)):
            bitmap = BufferedBitmap()
            raw = _BitmapLinearBuffer(bitmap, 128, swapped_storage=True)
            panel = MatrixPortalPanel(raw, 128, 0, 64, 32)
            expected = VirtualDisplay(64, 32)
            for y in range(32):
                for x in range(64):
                    panel.set_pixel565(x, y, (x * 1151 + y * 251) & 65535)
                    expected.set_pixel(x, y, panel.get_pixel(x, y))
                raw.pixels_view[y * 128 + 64:y * 128 + 128] = array("H", [y + 111] * 64)
            untouched = [bitmap[y * 128 + 64:y * 128 + 128] for y in range(32)]
            VisualLayerEngine(64, 32)._color_pipeline(expected, degrees, split, bright)
            apply(raw.pixels_view, 128, 0, 64, 32, True,
                  degrees, split, bright, numpy)
            for y in range(32):
                self.assertEqual(bitmap[y * 128 + 64:y * 128 + 128], untouched[y])
                for x in range(64):
                    actual = panel.get_pixel565(x, y)
                    wanted = rgb888_to_rgb565(expected.get_pixel(x, y))
                    # CircuitPython ulab uses float32; interpolation at a
                    # quantization boundary may differ by one channel step.
                    for mask, shift in ((31, 11), (63, 5), (31, 0)):
                        self.assertLessEqual(abs(((actual >> shift) & mask)
                                                 - ((wanted >> shift) & mask)), 1)

    def test_packed_color_pipeline_matches_original_rgb565_result(self):
        class BufferedBitmap(array):
            width = 8
            height = 2
            def __new__(cls):
                return array.__new__(cls, "H", [0] * 16)
        bitmap = BufferedBitmap()
        raw = _BitmapLinearBuffer(bitmap, stride=8, swapped_storage=True)
        panel = MatrixPortalPanel(raw, 8, 0, 4, 2)
        baseline = VirtualDisplay(4, 2)
        for y in range(2):
            for x in range(4):
                panel.set_pixel(x, y, (35+x*40, 25+y*90+x*15, 180-x*33))
                baseline.set_pixel(x, y, panel.get_pixel(x, y))
        for degrees, split, brighten in ((0, .5, 0), (75, 0, 0), (170, .4, .1)):
            for y in range(2):
                for x in range(4):
                    panel.set_pixel(x, y, baseline.get_pixel(x, y))
            expected = VirtualDisplay(4, 2)
            for y in range(2):
                for x in range(4):
                    expected.set_pixel(x, y, baseline.get_pixel(x, y))
            VisualLayerEngine(4, 2)._color_pipeline(expected, degrees, split, brighten)
            self.assertTrue(panel.native_color_pipeline(degrees, split, brighten))
            for y in range(2):
                for x in range(4):
                    self.assertEqual(panel.get_pixel565(x, y), rgb888_to_rgb565(expected.get_pixel(x, y)),
                                     (degrees, split, brighten, x, y))

    def test_verified_bitmap_buffer_uses_direct_pixels_in_display_order(self):
        class BufferedBitmap(array):
            width = 4
            height = 2
            def __new__(cls):
                return array.__new__(cls, "H", [0] * 8)
        bitmap = BufferedBitmap()
        buffer = _BitmapLinearBuffer(bitmap, stride=4, swapped_storage=True)
        self.assertIsNotNone(buffer.pixels_view)
        buffer[5] = 0xF800
        self.assertEqual(bitmap[5], 0x00F8)
        self.assertEqual(buffer[5], 0xF800)

    def test_native_spatial_uses_clipped_bitmaptools_transform(self):
        bitmap = FakeBitmap(128, 32, 65536)
        panel = MatrixPortalPanel(_BitmapLinearBuffer(bitmap, 128, True), 128, 0, 64, 32)
        calls = []
        tools = types.SimpleNamespace(
            blit=lambda *args, **kwargs: calls.append(("copy", kwargs)),
            rotozoom=lambda *args, **kwargs: calls.append(("transform", kwargs)),
        )
        with patch.dict(sys.modules, {"bitmaptools": tools,
             "displayio": types.SimpleNamespace(Bitmap=FakeBitmap)}):
            self.assertTrue(panel.native_spatial(.2, 2, -1))
        self.assertEqual([call[0] for call in calls], ["copy", "transform"])
        self.assertEqual(calls[1][1]["dest_clip1"], (64, 32))
        self.assertEqual(calls[1][1]["scale"], 1.2)

    def test_both_panels_map_to_distinct_halves_and_back_can_rotate(self):
        board = types.SimpleNamespace(
            MTX_ADDRESS=(0, 1, 2, 3),
            MTX_COMMON={"rgb_pins": (0, 1, 2, 3, 4, 5), "clock_pin": 0,
                        "latch_pin": 0, "output_enable_pin": 0},
        )
        displayio = types.SimpleNamespace(
            release_displays=lambda: None,
            Bitmap=FakeBitmap,
            ColorConverter=lambda **kwargs: None,
            Colorspace=types.SimpleNamespace(RGB565=1),
            Group=list,
            TileGrid=lambda bitmap, pixel_shader: bitmap,
        )
        framebufferio = types.SimpleNamespace(FramebufferDisplay=FakeFrameBufferDisplay)
        rgbmatrix = types.SimpleNamespace(RGBMatrix=FakeRGBMatrix)
        with patch.dict(sys.modules, {
            "board": board, "displayio": displayio, "rgbmatrix": rgbmatrix,
            "framebufferio": framebufferio,
        }):
            backend = MatrixPortalDisplayBackend(
                width=64, height=32, front_rotation=0, back_rotation=180
            )

        self.assertEqual(backend.matrix.kwargs["width"], 128)
        self.assertEqual(backend.matrix.kwargs["rgb_pins"], (0, 2, 1, 3, 5, 4))
        front = backend.get("front")
        back = backend.get("back")
        front.set_pixel(0, 0, (255, 0, 0))
        back.set_pixel(0, 0, (0, 0, 255))
        self.assertEqual(backend.framebuffer[0], 0xF800)
        self.assertEqual(backend.framebuffer[31 * 128 + 127], 0x001F)
        self.assertEqual(front.get_pixel(0, 0), (255, 0, 0))
        self.assertEqual(back.get_pixel(0, 0), (0, 0, 255))
        back.copy_from(front)
        self.assertEqual(back.get_pixel565(0, 0), front.get_pixel565(0, 0))
        self.assertEqual(backend.framebuffer[31 * 128 + 127], 0xF800)
        backend.present()
        self.assertEqual(backend.matrix.refresh_count, 2)

    def test_swapped_storage_native_blit_preserves_logical_colors(self):
        board = types.SimpleNamespace(
            MTX_ADDRESS=(0, 1, 2, 3),
            MTX_COMMON={"rgb_pins": (0, 1, 2, 3, 4, 5)},
        )
        colors = []
        displayio = types.SimpleNamespace(
            release_displays=lambda: None, Bitmap=FakeBitmap,
            ColorConverter=lambda **kwargs: colors.append(kwargs) or None,
            Colorspace=types.SimpleNamespace(RGB565=1, RGB565_SWAPPED=2),
            Group=list, TileGrid=lambda bitmap, pixel_shader: bitmap,
        )
        copied = []

        def blit(dest, source, x, y):
            copied.append((x, y))
            for py in range(source.height):
                for px in range(source.width):
                    dest[x + px, y + py] = source[px, py]

        with patch.dict(sys.modules, {
            "board": board, "displayio": displayio,
            "rgbmatrix": types.SimpleNamespace(RGBMatrix=FakeRGBMatrix),
            "framebufferio": types.SimpleNamespace(FramebufferDisplay=FakeFrameBufferDisplay),
            "bitmaptools": types.SimpleNamespace(blit=blit),
        }):
            backend = MatrixPortalDisplayBackend(swapped_storage=True)
            frame = FakeBitmap(64, 32, 65536)
            frame[0, 0] = 0x00F8
            backend.get("front").blit_rgb565_swapped(frame)
            backend.get("back").blit_rgb565_swapped(frame)

        self.assertEqual(colors[0]["input_colorspace"], 2)
        self.assertEqual(copied, [(0, 0), (64, 0)])
        self.assertEqual(backend.bitmap[0, 0], 0x00F8)
        self.assertEqual(backend.get("front").get_pixel565(0, 0), 0xF800)
        self.assertEqual(backend.get("back").get_pixel(0, 0), (255, 0, 0))
        backend.get("front").set_pixel(1, 1, (0, 0, 255))
        self.assertEqual(backend.bitmap[1, 1], 0x1F00)
        backend.get("front").dim(0.5)
        self.assertEqual(backend.get("front").get_pixel565(0, 0), 0x7800)
        self.assertEqual(backend.get("front").get_pixel565(1, 1), 0x000F)
        self.assertEqual(backend.get("back").get_pixel565(0, 0), 0xF800)

    def test_native_icon_blit_preserves_transparency_and_panel_boundary(self):
        board = types.SimpleNamespace(MTX_ADDRESS=(0, 1, 2, 3),
            MTX_COMMON={"rgb_pins": (0, 1, 2, 3, 4, 5)})
        displayio = types.SimpleNamespace(release_displays=lambda: None,
            Bitmap=FakeBitmap, ColorConverter=lambda **kwargs: None,
            Colorspace=types.SimpleNamespace(RGB565_SWAPPED=2),
            Group=list, TileGrid=lambda bitmap, pixel_shader: bitmap)
        calls = []
        def blit(dest, source, x, y, **kwargs):
            calls.append((x, y, kwargs))
            for py in range(kwargs["y1"], kwargs["y2"]):
                for px in range(kwargs["x1"], kwargs["x2"]):
                    value = source[px, py]
                    if value != kwargs.get("skip_source_index"):
                        dest[x + px - kwargs["x1"], y + py - kwargs["y1"]] = value
        def fill_region(dest, x1, y1, x2, y2, value):
            for py in range(y1, y2):
                for px in range(x1, x2):
                    dest[px, py] = value
        with patch.dict(sys.modules, {"board": board, "displayio": displayio,
             "bitmaptools": types.SimpleNamespace(blit=blit, fill_region=fill_region),
             "rgbmatrix": types.SimpleNamespace(RGBMatrix=FakeRGBMatrix),
             "framebufferio": types.SimpleNamespace(FramebufferDisplay=FakeFrameBufferDisplay)}):
            backend = MatrixPortalDisplayBackend(swapped_storage=True)
            front = backend.get("front")
            back = backend.get("back")
            front.fill((0, 0, 255))
            back.fill((0, 255, 0))
            asset = types.SimpleNamespace(pixels=(((255, 0, 0, 255), (0, 0, 0, 0)),))
            self.assertTrue(front.blit_icon(asset, 63, 0))
            self.assertEqual(front.get_pixel565(63, 0), 0xF800)
            self.assertEqual(back.get_pixel(0, 0), (0, 255, 0))
            self.assertTrue(front.blit_icon(asset, -1, 1))
            self.assertEqual(front.get_pixel565(0, 1), 0x001F)
            self.assertEqual(len(calls), 2)
            self.assertIs(asset._board_bitmap, asset._board_bitmap)
            back.copy_from(front)
            self.assertEqual(back.get_pixel565(63, 0), 0xF800)
            self.assertEqual(back.get_pixel565(0, 1), 0x001F)
            self.assertEqual(len(calls), 3)
            front.blit_glyph("A", ("01010", "10001", "11111", "10001",
                                   "10001", "10001", "10001"), 5, 5, (255, 0, 0), 1)
            first_cache_size = len(backend.framebuffer.glyph_cache)
            front.blit_glyph("A", ("01010", "10001", "11111", "10001",
                                   "10001", "10001", "10001"), 5, 5, (255, 0, 0), 1)
            self.assertEqual(len(backend.framebuffer.glyph_cache), first_cache_size)
            self.assertEqual(front.get_pixel565(6, 5), 0xF800)
            self.assertNotEqual(front.get_pixel565(5, 5), 0xF800)


if __name__ == "__main__":
    unittest.main()
