import unittest

from visual_engine import LAYER_KEYS, VisualLayerEngine


class VibePresetTests(unittest.TestCase):
    def setUp(self):
        self.engine = VisualLayerEngine(64, 32)

    def test_presets_keep_stable_layer_contract(self):
        expected = set(LAYER_KEYS)
        for name in ("Pulse", "Neon", "Spark", "Chaos"):
            preset = self.engine.preset(name)
            self.assertEqual(set(preset), expected)
            for value in preset.values():
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.5)

    def test_presets_have_distinct_musical_focus(self):
        pulse = self.engine.preset("Pulse")
        neon = self.engine.preset("Neon")
        spark = self.engine.preset("Spark")
        chaos = self.engine.preset("Chaos")

        self.assertGreater(pulse["bass_zoom"], neon["bass_zoom"])
        self.assertGreater(neon["mids_hue"], pulse["mids_hue"])
        self.assertGreater(spark["high_sparkle"], pulse["high_sparkle"])
        self.assertGreater(chaos["bass_shake"], pulse["bass_shake"])
        self.assertGreater(chaos["high_rgb_split"], spark["high_rgb_split"])

    def test_default_mapping_is_more_reserved_than_chaos(self):
        default = self.engine.default_layers()
        chaos = self.engine.preset("Chaos")
        self.assertLess(sum(default.values()), sum(chaos.values()))


if __name__ == "__main__":
    unittest.main()
