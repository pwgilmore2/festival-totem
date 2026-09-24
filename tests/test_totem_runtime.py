import unittest
from unittest.mock import patch

from display import VirtualDisplay
from runtime_io import SignalStore
from totem_runtime import TotemRuntime


class FakeMedia:
    def __init__(self, count=3):
        self.items = ["asset_%d.gif" % index for index in range(count)]
        self.selections = []
        self.handled = []
        self.rendered = []
        self.suspended = []

    def __len__(self):
        return len(self.items)

    def name(self, index):
        return self.items[index] if self.items else None

    def find_index(self, name):
        try:
            return self.items.index(name)
        except ValueError:
            return None

    def select(self, side, index):
        self.selections.append((side, int(index)))
        return True

    def render(self, side, index, display, t):
        self.rendered.append(side)
        value = 40 + int(index) * 20
        display.fill((value, 0, 0))

    def suspend(self, side):
        self.suspended.append(side)

    def info(self, index):
        if not self.items:
            return {
                "image_name": None,
                "image_mode": None,
                "image_settings": None,
                "image_tags": [],
                "image_favorite": False,
            }
        return {
            "image_name": self.items[index],
            "image_mode": "crop",
            "image_settings": {},
            "image_tags": [],
            "image_favorite": False,
        }

    def library_state(self):
        return [
            {"index": index, "name": name, "tags": [], "favorite": False}
            for index, name in enumerate(self.items)
        ]

    def reload(self):
        return None

    def handle_command(self, command, value, reference_index):
        self.handled.append((command, value, reference_index))
        return command == "desktop_only"


class FakeIcons:
    errors = []

    def __init__(self):
        self._names = ["Alien", "Eye"]

    def names(self):
        return list(self._names)

    def reload(self):
        return self


class FakeOverlay:
    def draw_text(self, *args, **kwargs):
        return None

    def draw_icon(self, *args, **kwargs):
        return None


def fill(display, t):
    display.fill((1, 2, 3))


EFFECTS = {"Rainbow": fill, "Plasma": fill}


class TotemRuntimeTests(unittest.TestCase):
    def test_text_transition_lifecycle(self):
        runtime, _ = self.make_runtime()
        runtime.set_target('front')
        with patch('totem_runtime.time.monotonic', return_value=100):
            runtime.show_text({'message': 'FIRST', 'scale': 1})
            self.assertIsNone(runtime.text_transitions['front']['previous'])
        with patch('totem_runtime.time.monotonic', return_value=101):
            runtime._update_text_transitions()
            runtime.set_text_settings({'message': 'NEXT', 'scale': 2, 'font': 'Block'})
            transition = runtime.text_transitions['front']
            self.assertEqual(transition['previous']['message'], 'FIRST')
            self.assertEqual(transition['previous']['scale'], 1)
            runtime.set_text_settings({'message': 'NEXT', 'scale': 2, 'font': 'Block'})
            self.assertIs(runtime.text_transitions['front'], transition)
        with patch('totem_runtime.time.monotonic', return_value=102):
            runtime._update_text_transitions()
            runtime.set_overlay_background('Black')
            runtime.hide_text()
            self.assertFalse(runtime.panels['front']['text']['enabled'])
            self.assertTrue(runtime._black_background('front'))
            self.assertEqual(runtime.text_transitions['front']['previous']['message'], 'NEXT')
        with patch('totem_runtime.time.monotonic', return_value=103):
            runtime._update_text_transitions()
            self.assertIsNone(runtime.text_transitions['front'])
            self.assertFalse(runtime._black_background('front'))

    def make_runtime(self, media_count=3):
        displays = {
            "front": VirtualDisplay(64, 32),
            "back": VirtualDisplay(64, 32),
        }
        media = FakeMedia(media_count)
        runtime = TotemRuntime(
            64,
            32,
            displays,
            media,
            FakeIcons(),
            FakeOverlay(),
            EFFECTS,
            signal_store=SignalStore(),
        )
        return runtime, media

    def test_initial_front_back_media_are_independent(self):
        runtime, _ = self.make_runtime(3)
        front = runtime.panels["front"]["image_index"]
        back = runtime.panels["back"]["image_index"]
        self.assertNotEqual(front, back)

    def test_info_scenes_release_gif_and_resume_on_return(self):
        runtime, media = self.make_runtime()
        runtime.handle_command({"command": "info_scene", "value": "Clock"})
        self.assertEqual(media.suspended[-2:], ["front", "back"])
        runtime.step(.016, 1)
        self.assertEqual(media.rendered, [])
        self.assertEqual(runtime.phone_panel("front")["info_scene"], "Clock")
        runtime.handle_command({"command": "scene_background", "value": {"scene": "Clock", "background": "Black"}})
        self.assertEqual(runtime.info_scenes.backgrounds["Clock"], "Black")
        runtime.handle_command({"command": "info_scene", "value": None})
        runtime.step(.016, 2)
        self.assertIn("front", media.rendered)
        self.assertIn("back", media.rendered)

    def test_schedule_batches_preserve_multiple_days(self):
        runtime, _ = self.make_runtime()
        runtime.handle_command({"command": "schedule_update", "value": [{"day": "2026-09-30", "name": "One"}]})
        runtime.handle_command({"command": "schedule_append", "value": [{"day": "2026-10-02", "name": "Two"}]})
        runtime.handle_command({"command": "schedule_day", "value": "2026-10-02"})
        self.assertEqual(runtime.info_scenes.day_schedule()[0]["name"], "Two")
        runtime.handle_command({"command": "schedule_day", "value": "Auto"})
        self.assertEqual(len(runtime.info_scenes.schedule), 2)

    def test_mirror_only_renders_front_and_suspends_back_stream(self):
        runtime, media = self.make_runtime()
        runtime.handle_command({"command": "mirror_displays", "value": True})
        self.assertIn("back", media.suspended)
        runtime.step(.016, 1)
        self.assertEqual(media.rendered, ["front"])
        self.assertEqual(runtime.displays["front"].pixels, runtime.displays["back"].pixels)
        self.assertEqual(runtime.phone_panel("front"), runtime.phone_panel("back"))
        runtime.handle_command({"command": "mirror_displays", "value": False})
        runtime.step(.016, 2)
        self.assertEqual(media.rendered[-2:], ["front", "back"])

    def test_black_icon_background_suspends_gif_without_hiding_icon(self):
        runtime, media = self.make_runtime()
        runtime.handle_command({"command": "set_target", "value": "front"})
        runtime.handle_command({"command": "icon_background", "value": "Black"})
        runtime.handle_command({"command": "icon_toggle", "value": "Alien"})
        runtime.step(.016, 1)
        self.assertIn("front", media.suspended)
        self.assertEqual(media.rendered, ["back"])
        self.assertTrue(runtime.phone_panel("front")["icon"]["icon_enabled"])

    def test_targeted_text_and_icon_remain_exclusive(self):
        runtime, _ = self.make_runtime()
        runtime.set_target("front")
        runtime.handle_command(
            {
                "command": "text_show",
                "value": {"message": "HELLO", "font": "Pixel"},
            }
        )
        self.assertTrue(runtime.panels["front"]["text"]["enabled"])
        self.assertFalse(runtime.panels["back"]["text"]["enabled"])

        runtime.handle_command({"command": "icon_toggle", "value": "Alien"})
        self.assertTrue(runtime.panels["front"]["icon"]["icon_enabled"])
        self.assertFalse(runtime.panels["front"]["text"]["enabled"])

    def test_dimmed_gif_reduces_image_before_text_overlay(self):
        runtime, _ = self.make_runtime()
        runtime.handle_command({"command": "effect", "value": "Image"})
        for frame in range(70):
            runtime.step(.016, frame)
        original = runtime.displays["front"].get_pixel(0, 0)
        back_original = runtime.displays["back"].get_pixel(0, 0)
        runtime.set_target("front")
        runtime.handle_command({"command": "text_show", "value": {"message": "HELLO", "background": "Dimmed GIF"}})
        runtime.step(.016, 70)
        self.assertGreater(original[0], 0)
        self.assertEqual(runtime.displays["front"].get_pixel(0, 0), (int(original[0] * .65), 0, 0))
        self.assertEqual(runtime.displays["back"].get_pixel(0, 0), back_original)

    def test_shared_overlay_background_controls_both_icons_and_text(self):
        runtime, media = self.make_runtime()
        runtime.handle_command({"command": "effect", "value": "Image"})
        for frame in range(70):
            runtime.step(.016, frame)
        runtime.handle_command({"command": "icon_toggle", "value": "Alien"})
        runtime.step(.016, 70)
        dimmed = runtime.displays["front"].get_pixel(0, 0)[0]
        runtime.handle_command({"command": "overlay_background", "value": "None"})
        runtime.content_transitions["front"].active = False
        runtime.step(.016, 71)
        self.assertGreater(runtime.displays["front"].get_pixel(0, 0)[0], dimmed)
        runtime.handle_command({"command": "overlay_background", "value": "Black"})
        runtime.step(.016, 72)
        self.assertTrue(runtime._media_suspended["front"])
        self.assertEqual(runtime.controller_state()["overlay_background"], "Black")
        runtime.handle_command({"command": "text_show", "value": {"message": "HEY", "background": "Dimmed GIF"}})
        self.assertTrue(runtime._black_background("front"))
        runtime.handle_command({"command": "overlay_background", "value": "None"})
        runtime.step(.016, 73)
        self.assertFalse(runtime._media_suspended["front"])

    def test_overlay_audio_is_shared_and_text_payload_cannot_override_it(self):
        runtime, _ = self.make_runtime()
        runtime.handle_command({"command": "overlay_audio_reactivity", "value": "Intense"})
        runtime.handle_command({"command": "text_show", "value": {"message": "HEY", "audio_reactivity": "Off"}})
        self.assertEqual(runtime.controller_state()["overlay_audio_reactivity"], "Intense")
        self.assertEqual(runtime.panels["front"]["text"]["audio_reactivity"], "Intense")
        runtime.handle_command({"command": "overlay_audio_reactivity", "value": "Subtle"})
        runtime.step(.016, 1)
        self.assertEqual(runtime.panels["front"]["text"]["audio_reactivity"], "Subtle")

    def test_controller_state_preserves_phone_contract(self):
        runtime, _ = self.make_runtime()
        state = runtime.controller_state()
        self.assertEqual(state["target"], "both")
        self.assertIn("front", state["panels"])
        self.assertIn("back", state["panels"])
        self.assertIn("library", state)
        self.assertIn("overlay_icons", state)
        self.assertIn("guest", state)
        self.assertEqual(state["image_count"], 3)

    def test_unknown_command_delegates_to_media_adapter(self):
        runtime, media = self.make_runtime()
        handled = runtime.handle_command(
            {"command": "desktop_only", "value": {"x": 1}}
        )
        self.assertTrue(handled)
        self.assertEqual(media.handled[-1][0], "desktop_only")

    def test_render_pipeline_builds_transition_snapshots(self):
        runtime, _ = self.make_runtime()
        runtime.step(1.0 / 60.0, 1)
        self.assertIsNotNone(runtime.content_snapshots["front"])
        self.assertIsNotNone(runtime.scene_snapshots["front"])
        self.assertEqual(len(runtime.content_snapshots["front"]), 32)
        self.assertEqual(len(runtime.content_snapshots["front"][0]), 64)


if __name__ == "__main__":
    unittest.main()
