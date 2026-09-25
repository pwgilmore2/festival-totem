"""Desktop regression test for the two-panel MatrixPortal mapping."""

import sys
import types
import unittest
from unittest.mock import patch

from matrixportal_backend import MatrixPortalDisplayBackend


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

    def __getitem__(self, xy):
        x, y = xy
        return self.data[y * self.width + x]

    def __setitem__(self, xy, value):
        x, y = xy
        self.data[y * self.width + x] = value


class FakeFrameBufferDisplay:
    def __init__(self, matrix, auto_refresh=False):
        self.matrix = matrix
        self.root_group = None

    def refresh(self):
        self.matrix.refresh()


class MatrixPortalBackendTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
