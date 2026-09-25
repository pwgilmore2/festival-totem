"""Desktop regression test for the two-panel MatrixPortal mapping."""

import sys
import types
import unittest
from array import array
from unittest.mock import patch

from matrixportal_backend import MatrixPortalDisplayBackend, MatrixPortalPanel, _BitmapLinearBuffer, _swap16, rgb888_to_rgb565, rgb565_to_rgb888
from display import VirtualDisplay
from visual_engine import VisualLayerEngine
from runtime_random import _SeededRandom


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
    def test_native_dim_filters_only_selected_face(self):
        class Bitmap:
            def __init__(self, width, height, colors=65536):
                self.width, self.height = width, height
                self.data = array('H', [0] * (width * height))
            def __getitem__(self, xy):
                x, y = xy
                return self.data[y * self.width + x]
            def __setitem__(self, xy, value):
                x, y = xy
                self.data[y * self.width + x] = value
        def blit(dst, src, dx, dy, *, x1=0, y1=0, x2=None, y2=None):
            for sy in range(y1, src.height if y2 is None else y2):
                for sx in range(x1, src.width if x2 is None else x2):
                    dst[dx + sx - x1, dy + sy - y1] = src[sx, sy]
        mix_calls = []
        def mix(bitmap, weights):
            mix_calls.append(weights)
            for index, value in enumerate(bitmap.data):
                color = _swap16(value)
                scale = int(weights[0] * 256)
                result = ((((color >> 11) & 31) * scale >> 8) << 11
                          | ((((color >> 5) & 63) * scale >> 8) << 5)
                          | ((color & 31) * scale >> 8))
                bitmap.data[index] = _swap16(result)
        bmp = Bitmap(128, 32)
        fb = _BitmapLinearBuffer(bmp, 128, swapped_storage=True)
        fb.pixels_view = memoryview(bmp.data)
        front = MatrixPortalPanel(fb, 128, 0, 64, 32)
        for y in range(32):
            for x in range(128):
                bmp[x, y] = _swap16(0xF81F)
        with patch.dict(sys.modules, {
            'bitmaptools': types.SimpleNamespace(blit=blit),
            'bitmapfilter': types.SimpleNamespace(ChannelScale=lambda *args: args, mix=mix),
            'displayio': types.SimpleNamespace(Bitmap=Bitmap),
        }):
            front.dim(.5)
        self.assertEqual(mix_calls, [(.5, .5, .5)])
        self.assertEqual(front.get_pixel565(0, 0), 0x780F)
        self.assertEqual(bmp[64, 0], _swap16(0xF81F))

    def test_styled_glyphs_match_desktop_shapes_with_cached_native_blits(self):
        from text_engine import TextRenderer
        from text import FONT
        class Bitmap:
            def __init__(self, width, height, colors=65536):
                self.width, self.height = width, height
                self.data = array('H', [0] * (width * height))
            def __getitem__(self, xy):
                x, y = xy
                return self.data[y * self.width + x]
            def __setitem__(self, xy, value):
                x, y = xy
                self.data[y * self.width + x] = value
            def fill(self, value):
                self.data[:] = array('H', [value] * len(self.data))
        def blit(dst, src, dx, dy, *, x1, y1, x2, y2, skip_source_index):
            for sy in range(y1, y2):
                for sx in range(x1, x2):
                    value = src[sx, sy]
                    if value != skip_source_index:
                        dst[dx + sx - x1, dy + sy - y1] = value
        fb_bitmap = Bitmap(128, 32)
        fb = _BitmapLinearBuffer(fb_bitmap, 128, swapped_storage=True)
        fb.pixels_view = memoryview(fb_bitmap.data)
        panel = MatrixPortalPanel(fb, 128, 0, 64, 32)
        renderer = TextRenderer(64, 32)
        with patch.dict(sys.modules, {
            'displayio': types.SimpleNamespace(Bitmap=Bitmap),
            'bitmaptools': types.SimpleNamespace(blit=blit),
        }):
            for font in ('Block', 'Thin', 'Arcade', 'Quest'):
                reference = VirtualDisplay()
                fb_bitmap.fill(0)
                renderer._draw_glyph(reference, 'R', 8, 4, (121, 200, 86), 2, font)
                renderer._draw_glyph(panel, 'R', 8, 4, (121, 200, 86), 2, font)
                count = len(fb.glyph_cache)
                renderer._draw_glyph(panel, 'R', 8, 4, (121, 200, 86), 2, font)
                self.assertEqual(len(fb.glyph_cache), count)
                for y in range(20):
                    for x in range(24):
                        actual = panel.get_pixel(x, y)
                        expected = reference.get_pixel(x, y)
                        self.assertLessEqual(max(abs(a - b) for a, b in zip(actual, expected)),
                                             7, (font, x, y, actual, expected))

    def test_packed_content_transitions_match_rgb_reference(self):
        from transition_engine import TransitionManager

        class Bitmap:
            width, height = 128, 32
            def __init__(self):
                self.data = array('H', [0x4a4a] * (128 * 32))
        for kind in ("Fade", "Melt", "Dissolve", "Glitch", "Ripple", "Zoom", "Wipe"):
            bitmap = Bitmap()
            fb = _BitmapLinearBuffer(bitmap, 128, swapped_storage=True)
            fb.pixels_view = memoryview(bitmap.data)
            panel = MatrixPortalPanel(fb, 128, 0, 64, 32)
            reference = VirtualDisplay()
            for y in range(32):
                for x in range(64):
                    value = ((x * 4) % 256, (y * 7) % 256, ((x + y) * 3) % 256)
                    reference.set_pixel(x, y, value)
                    fb[y * 128 + x] = rgb888_to_rgb565(value)
            native_manager = TransitionManager(64, 32)
            rgb_manager = TransitionManager(64, 32)
            native_manager.begin(panel, kind, 1)
            rgb_manager.begin(reference, kind, 1)
            native_manager.seed = rgb_manager.seed = 127
            native_manager.elapsed = rgb_manager.elapsed = .42
            for y in range(32):
                for x in range(64):
                    value = (((x + y) * 5) % 256, (x * 3) % 256, (y * 8) % 256)
                    reference.set_pixel(x, y, value)
                    fb[y * 128 + x] = rgb888_to_rgb565(value)
            native_manager.apply(panel)
            rgb_manager.apply(reference)
            for y in range(32):
                for x in range(64):
                    expected, actual = reference.get_pixel(x, y), panel.get_pixel(x, y)
                    self.assertLessEqual(max(abs(a - b) for a, b in zip(expected, actual)),
                                         18, (kind, x, y, actual, expected))
                self.assertEqual(bitmap.data[y * 128 + 64:(y + 1) * 128],
                                 array('H', [0x4a4a] * 64))

    def test_packed_remaps_and_dim_preserve_back_panel(self):
        class Bitmap:
            width, height = 128, 32
            def __init__(self):
                self.data = array('H', [0] * (128 * 32))
        bitmap = Bitmap()
        fb = _BitmapLinearBuffer(bitmap, 128, swapped_storage=True)
        fb.pixels_view = memoryview(bitmap.data)
        panel = MatrixPortalPanel(fb, 128, 0, 64, 32)
        for y in range(32):
            for x in range(64):
                bitmap.data[y * 128 + x] = _swap16((x << 5) | y)
                bitmap.data[y * 128 + 64 + x] = 0x4a4a
        self.assertTrue(panel.native_pixel_melt([2] * 64))
        self.assertEqual(bitmap.data[3 * 128 + 4], _swap16((4 << 5) | 1))
        self.assertTrue(panel.native_jumble(list(reversed(range(128))), 4, 16, 8))
        self.assertEqual(bitmap.data[0], _swap16((60 << 5) | 26))
        panel.dim(.5)
        self.assertEqual(bitmap.data[64], 0x4a4a)
        self.assertEqual(bitmap.data[31 * 128 + 127], 0x4a4a)

    def test_packed_effects_match_original_colors_and_only_write_one_panel(self):
        import matrixportal_effects as effects
        from runtime_random import _SeededRandom

        class Bitmap:
            width, height = 128, 32
            def __init__(self):
                self.data = array('H', [0x4a4a] * (self.width * self.height))
            def __setitem__(self, xy, value):
                x, y = xy
                self.data[y * self.width + x] = value

        def fill_region(bitmap, x1, y1, x2, y2, value):
            for y in range(y1, y2):
                for x in range(x1, x2):
                    bitmap[x, y] = value

        for name, render in effects.EFFECTS.items():
            bitmap = Bitmap()
            fb = _BitmapLinearBuffer(bitmap, 128, swapped_storage=True)
            fb.pixels_view = memoryview(bitmap.data)
            front = MatrixPortalPanel(fb, 128, 0, 64, 32)
            original = VirtualDisplay()
            with patch.dict(sys.modules, {'bitmaptools': types.SimpleNamespace(fill_region=fill_region)}), \
                    patch.object(effects.random, 'Random', _SeededRandom):
                render(original, 1.5)
                render(front, 1.5)
            for y in range(32):
                for x in range(64):
                    actual = rgb565_to_rgb888(_swap16(bitmap.data[y * 128 + x]))
                    expected = original.get_pixel(x, y)
                    self.assertLessEqual(max(abs(a - b) for a, b in zip(actual, expected)),
                                         18, (name, x, y, actual, expected))
                self.assertEqual(bitmap.data[y * 128 + 64:(y + 1) * 128],
                                 array('H', [0x4a4a] * 64))

    def test_native_row_wave_shifts_each_row_with_clamped_edges(self):
        import math
        class Bitmap:
            def __init__(self, width, height, colors):
                self.width, self.height = width, height
                self.data = [0] * (width * height)
            def __getitem__(self, xy):
                x, y = xy
                return self.data[y * self.width + x]
            def __setitem__(self, xy, value):
                x, y = xy
                self.data[y * self.width + x] = value

        bitmap = Bitmap(128, 32, 65536)
        for y in range(32):
            for x in range(64):
                bitmap[x, y] = y * 64 + x
                bitmap[x + 64, y] = 41700 + x
        buffer = _BitmapLinearBuffer(bitmap, 128, swapped_storage=True)
        panel = MatrixPortalPanel(buffer, 128, 0, 64, 32)

        def blit(dst, src, dx, dy, *, x1=0, y1=0, x2=None, y2=None):
            for sy in range(y1, src.height if y2 is None else y2):
                for sx in range(x1, src.width if x2 is None else x2):
                    dst[dx + sx - x1, dy + sy - y1] = src[sx, sy]
        def fill(dst, x1, y1, x2, y2, value):
            for y in range(y1, y2):
                for x in range(x1, x2):
                    dst[x, y] = value
        weights = []
        tools = types.SimpleNamespace(blit=blit, fill_region=fill)
        filters = types.SimpleNamespace(
            mix=lambda bitmap, matrix: weights.append(matrix),
            ChannelMixer=lambda *values: values)
        with patch.dict(sys.modules, {"bitmaptools": tools,
                                      "displayio": types.SimpleNamespace(Bitmap=Bitmap),
                                      "bitmapfilter": filters}):
            self.assertTrue(panel.native_row_wave(.6, 39, speed=.028, frequency=.31))
            amp = max(1, int(1 + .6 * 5))
            for y in range(32):
                shift = int(math.sin(y * .31 + 39 * .028) * amp)
                for x in range(64):
                    sx = max(0, min(63, x - shift))
                    self.assertEqual(bitmap[x, y], y * 64 + sx)
                    self.assertEqual(bitmap[x + 64, y], 41700 + x)
            self.assertTrue(panel.native_row_wave(.6, 39, "teal", .032, .34))
            self.assertEqual(weights, [(0.44, 0, 0, 0, 1.04, 0.15, 0, 0, 1.10),
                                       (1, 0, 0, 0, 1, 0, 0, 0.05, 1)])

    def test_native_sparkles_match_board_seeded_points_and_preserve_other_face(self):
        class BufferedBitmap(array):
            width = 128
            height = 32

            def __new__(cls):
                return array.__new__(cls, "H", [0] * (128 * 32))

        bitmap = BufferedBitmap()
        raw = _BitmapLinearBuffer(bitmap, 128, swapped_storage=True)
        panel = MatrixPortalPanel(raw, 128, 0, 64, 32)
        for seed, amount in ((31, .4), (932, 1.0), (2391, .12)):
            for i in range(4096):
                bitmap[i] = 0
            with patch("visual_engine.random.Random", _SeededRandom):
                baseline = VirtualDisplay(64, 32)
                VisualLayerEngine(64, 32)._sparkles(baseline, amount, seed)
            self.assertTrue(panel.native_sparkles(amount, seed))
            for y in range(32):
                self.assertEqual(bitmap[y * 128 + 64:y * 128 + 128],
                                 array("H", [0] * 64))
                for x in range(64):
                    self.assertEqual(panel.get_pixel565(x, y),
                                     rgb888_to_rgb565(baseline.get_pixel(x, y)))

    def test_native_color_matrix_matches_hue_rotation_and_split_edges(self):
        from matrixportal_native_colors import apply, hue_weights

        self.assertEqual(hue_weights(0), (1, 0, 0, 0, 1, 0, 0, 0, 1))
        self.assertEqual(hue_weights(120), (0, 1, 0, 0, 0, 1, 0, 0, 1))
        self.assertEqual(hue_weights(240), (0, 0, 1, 1, 0, 0, 0, 1, 0))

        # The native compositor must sample one face, clamp the shifted edge,
        # blend all three isolated channels, then commit only to that face.
        calls = []
        class Bitmap:
            def __init__(self, width, height, colors):
                self.width, self.height = width, height
        framebuffer = types.SimpleNamespace(bitmap=Bitmap(128, 32, 65536),
                                            native_color_bitmaps=None)
        def blit(*args, **kwargs):
            calls.append(("blit", args, kwargs))
        def blend(dest, source1, source2, colorspace, factor1, factor2, *, blendmode):
            calls.append(("blend", (dest, source1, source2, colorspace,
                                     factor1, factor2), {"blendmode": blendmode}))
        filters = types.SimpleNamespace(
            mix=lambda *args: calls.append(("mix", args, {})),
            ChannelScale=lambda *weights: weights,
            ChannelMixer=lambda *weights: weights,
        )
        tools = types.SimpleNamespace(blit=blit, alphablend=blend,
                                      BlendMode=types.SimpleNamespace(Screen="screen"))
        displayio = types.SimpleNamespace(Bitmap=Bitmap,
                             Colorspace=types.SimpleNamespace(RGB565_SWAPPED="swapped"))
        with patch.dict(sys.modules, {"bitmaptools": tools,
                                      "bitmapfilter": filters,
                                      "displayio": displayio}):
            self.assertTrue(apply(framebuffer, 64, 64, 32, 0, .5, 0))
            self.assertEqual(sum(call[0] == "blend" for call in calls), 2)
            for operation, args, kwargs in calls:
                if operation == "blend":
                    self.assertEqual(args[4:], (1.0, 1.0))
                    self.assertEqual(kwargs, {"blendmode": "screen"})
            self.assertEqual([call[1][1] for call in calls if call[0] == "mix"],
                             [(1, 0, 0), (0, 0, 1), (0, 1, 0)])
            self.assertEqual(calls[0][2]["x1"], 64)
            self.assertEqual(calls[-1][1][1:], (framebuffer.native_color_bitmaps[0], 64, 0))
            self.assertFalse(apply(framebuffer, 0, 64, 32, 75, .5, 0))

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
