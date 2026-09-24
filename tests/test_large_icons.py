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
    def test_desktop_and_hardware_read_the_same_sample(self):
        desktop = IconLibrary().get("Liquid Stranger")
        hardware = EmbeddedIconLibrary().get("Liquid Stranger")
        self.assertIsNotNone(desktop)
        self.assertEqual(desktop.pixels, hardware.pixels)
        self.assertEqual((len(desktop.pixels[0]), len(desktop.pixels)), (60, 28))
        self.assertIn("Alien", IconLibrary().names())
        self.assertIn("Liquid Stranger", _icon_preview_data())

    def test_legacy_folder_requires_32x32_and_large_folder_rejects_oversize(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            large = directory / "large"
            large.mkdir()
            Image.new("RGBA", (60, 28)).save(directory / "wrong.png")
            Image.new("RGBA", (65, 28)).save(large / "too_wide.png")
            Image.new("RGBA", (64, 32)).save(large / "full.png")
            library = IconLibrary(directory)
            self.assertIn("Full", library.names())
            self.assertIn("Alien", library.names())
            self.assertEqual(len(library.errors), 2)

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
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + width, 64)
                self.assertLessEqual(y + height, 32)
                display = VirtualDisplay()
                renderer.draw_icon(display, {"icon_enabled": True, "icon": name, "motion": motion},
                                   {"audio_reactivity": "Reactive"}, t,
                                   signals={"bass": 1, "mids": 1, "beat": True})
                self.assertTrue(any(pixel != (0, 0, 0) for row in display.pixels for pixel in row))


if __name__ == "__main__":
    unittest.main()
