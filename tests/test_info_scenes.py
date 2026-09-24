import unittest

from display import VirtualDisplay
from info_scenes import InfoScenes, clean_schedule


class InfoScenesTests(unittest.TestCase):
    def test_clock_requires_valid_time_and_scenes_draw_without_assets(self):
        scenes = InfoScenes(64, 32)
        panel = VirtualDisplay()
        scenes.render("Clock", panel, 0)
        self.assertEqual(panel.get_pixel(4, 5), (0, 0, 0))
        scenes.backgrounds["Clock"] = "Sky"
        scenes.render("Clock", panel, 0)
        self.assertFalse(scenes.sync_time(0))
        self.assertTrue(scenes.sync_time(1790000000))
        scenes.render("Clock", panel, 0)
        self.assertIsNotNone(scenes.local_time())
        self.assertTrue(any(any(pixel != (0, 0, 0) for pixel in row) for row in panel.pixels))

    def test_schedule_sanitizes_and_weather_uses_manual_input(self):
        scenes = InfoScenes(64, 32)
        scenes.schedule = clean_schedule([{"time": "9:30 PM", "name": "Performer"}, {"name": "Missing"}])
        self.assertEqual(len(scenes.schedule), 1)
        panel = VirtualDisplay()
        scenes.render("Set Times", panel, 0)
        scenes.set_weather({"temperature": "72", "condition": "Cloudy"})
        scenes.render("Weather", panel, 0)
        self.assertEqual(scenes.weather, {"temperature": "72", "condition": "Cloudy"})
        scenes.set_weather({"temperature": "999", "condition": "Unknown"})
        self.assertEqual(scenes.weather, {"temperature": "", "condition": "Clear"})

    def test_waveform_accepts_normalized_signal_shape(self):
        scenes = InfoScenes(64, 32)
        panel = VirtualDisplay()
        scenes.render("Waveform", panel, 1, {"bass": .8, "mids": .2, "highs": .6, "volume": .7, "beat": True})
        self.assertTrue(any(any(pixel != (0, 0, 0) for pixel in row) for row in panel.pixels))


if __name__ == "__main__":
    unittest.main()
