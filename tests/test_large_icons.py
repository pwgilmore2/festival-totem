import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from display import VirtualDisplay
from embedded_icon_library import EmbeddedIconLibrary
from icon_assets import IconLibrary
from overlay_engine import OverlayRenderer
from overlay_ui_patch import _icon_preview_data


class LargeIconTests(unittest.TestCase):
    def test_audio_changes_text_brightness_without_changing_glyph_shape(self):
        renderer = OverlayRenderer(64, 32, IconLibrary())
        base = {"message": "HELLO", "font": "Pixel", "color_mode": "Solid",
                "color": "#ffffff", "scale": 1, "backplate": False}
        quiet = VirtualDisplay(64, 32)
        intense = VirtualDisplay(64, 32)
        renderer.draw_text(quiet, {**base, "audio_reactivity": "Off"}, 0,
                           signals={"bass": 0, "highs": 0, "beat": False})
        renderer.draw_text(intense, {**base, "audio_reactivity": "Intense"}, 0,
                           signals={"bass": 0, "highs": 0, "beat": False})
        mask = lambda display: {(x, y) for y, row in enumerate(display.pixels)
                                for x, pixel in enumerate(row) if pixel != (0, 0, 0)}
        self.assertEqual(mask(quiet), mask(intense))
        self.assertLess(sum(intense.get_pixel(x, y)[0] for x, y in mask(intense)),
                        sum(quiet.get_pixel(x, y)[0] for x, y in mask(quiet)))

    def test_desktop_and_hardware_read_the_same_sample(self):
        desktop = IconLibrary().get("Liquid Stranger")
        hardware = EmbeddedIconLibrary().get("Liquid Stranger")
        self.assertIsNotNone(desktop)
        self.assertEqual(desktop.pixels, hardware.pixels)
        self.assertEqual((len(desktop.pixels[0]), len(desktop.pixels)), (60, 28))
        self.assertIn("Alien", IconLibrary().names())
        self.assertIn("Liquid Stranger", _icon_preview_data())

    def test_both_folders_accept_small_canvas_overflow_but_reject_large_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            large = directory / "large"
            large.mkdir()
            Image.new("RGBA", (36, 35)).save(directory / "bordered_32x32.png")
            Image.new("RGBA", (41, 32)).save(directory / "too_wide.png")
            Image.new("RGBA", (68, 36)).save(large / "oversized.png")
            Image.new("RGBA", (73, 28)).save(large / "much_too_wide.png")
            Image.new("RGBA", (64, 32)).save(large / "full.png")
            library = IconLibrary(directory)
            self.assertIn("Full", library.names())
            self.assertIn("Bordered", library.names())
            self.assertIn("Oversized", library.names())
            self.assertEqual((len(library.get("Bordered").pixels[0]), len(library.get("Bordered").pixels)), (36, 35))
            self.assertEqual(len(library.errors), 2)

    def test_oversized_canvases_center_and_clip_slightly_during_motion(self):
        renderer = OverlayRenderer(64, 32, IconLibrary())
        self.assertEqual(renderer._icon_origin({"motion": "Orbit"}, 0, 32, 32), (24, 0))
        self.assertEqual(renderer._icon_origin({"motion": "Orbit"}, 0, 68, 36), (0, -2))
        self.assertEqual(renderer._icon_origin({"motion": "Bounce"}, 0, 68, 36), (-2, -1))
        self.assertEqual(renderer._icon_origin({"motion": "Orbit"}, 0, 64, 32), (2, 0))
        with tempfile.TemporaryDirectory() as tmp:
            large = Path(tmp) / "large"
            large.mkdir()
            Image.new("RGBA", (68, 36), (255, 0, 0, 255)).save(large / "oversized.png")
            display = VirtualDisplay()
            renderer = OverlayRenderer(64, 32, IconLibrary(tmp))
            renderer.draw_icon(display, {"icon_enabled": True, "icon": "Oversized", "motion": "Bounce"},
                               {"audio_reactivity": "Off"}, 0)
            self.assertEqual(display.get_pixel(0, 0), (255, 0, 0))
            self.assertEqual(display.get_pixel(63, 31), (255, 0, 0))

    def test_large_icon_remains_on_panel_through_orbit_bounce_and_audio(self):
        renderer = OverlayRenderer(64, 32, IconLibrary())
        for name in ("Liquid Stranger", "Full"):
            if name == "Full":
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "large"
                    path.mkdir()
                    Image.new("RGBA", (64, 32), (255, 0, 0, 255)).save(path / "full.png")
                    self._check_motion(OverlayRenderer(64, 32, IconLibrary(tmp)), name)
            else:
                self._check_motion(renderer, name)

    def _check_motion(self, renderer, name):
        asset = renderer.icon_library.get(name)
        width, height = len(asset.pixels[0]), len(asset.pixels)
        for motion in ("Orbit", "Bounce"):
            for t in (0, math.pi / 2, math.pi, 2 * math.pi):
                x, y = renderer._icon_origin({"motion": motion}, t, width, height)
                if width < 64:
                    self.assertGreaterEqual(x, 0)
                    self.assertLessEqual(x + width, 64)
                if height < 32:
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(y + height, 32)
                display = VirtualDisplay()
                renderer.draw_icon(display, {"icon_enabled": True, "icon": name, "motion": motion},
                                   {"audio_reactivity": "Reactive"}, t,
                                   signals={"bass": 1, "mids": 1, "beat": True})
                self.assertTrue(any(pixel != (0, 0, 0) for row in display.pixels for pixel in row))


if __name__ == "__main__":
    unittest.main()
