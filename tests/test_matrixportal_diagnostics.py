"""Validate staging, low-rate reporting and safe Wi-Fi credential reuse."""

import contextlib
import io
import json
import types
import unittest
from unittest.mock import patch

import matrixportal_diagnostics as diagnostic
from tools.run_matrixportal_diagnostics import private_program


class DiagnosticTests(unittest.TestCase):
    def test_preserves_private_password_with_comment_and_hash(self):
        template = 'WIFI_PASSWORD = ""  # private\nFPS = 30\n'
        installed = 'WIFI_PASSWORD = "a#password" # my secret\n'
        result = private_program(template, installed)
        self.assertIn('WIFI_PASSWORD = \'a#password\'', result)
        self.assertNotIn('my secret', result)
        self.assertEqual(result.count('WIFI_PASSWORD ='), 1)
        with self.assertRaises(ValueError):
            private_program(template, 'WIFI_PASSWORD = ""\n')

    def test_tour_covers_all_features_and_completes(self):
        class FakeRuntime:
            def __init__(self):
                self.base_effects = {'Rainbow': None}
                self.scenes = {'Chill': {}}
                self.icon_library = types.SimpleNamespace(names=lambda: ['Eye'])
                self.chaos_engine = types.SimpleNamespace(_clear=lambda: None,
                    trigger=lambda value: None, update_xy=lambda value: None)
                self.info_scenes = types.SimpleNamespace(sync_time=lambda value: None,
                    set_weather=lambda value: None, schedule=[])
                self.signal_store = types.SimpleNamespace(update_audio=lambda value: None)
                self.panels = {'front': {'image_index': 0}, 'back': {'image_index': 0}}
                self.content_transitions = {s: types.SimpleNamespace(active=False, source=None)
                                            for s in self.panels}
                self.scene_transitions = {s: types.SimpleNamespace(active=False, source=None)
                                          for s in self.panels}
                self.mirrored = True
                self.effect = 'Image'

            def _stop_show(self, side):
                pass

            def _set_icon_enabled(self, *args):
                pass

            def set_mirrored(self, enabled):
                self.mirrored = enabled

            def set_effect(self, value):
                self.effect = value

            def select_image(self, index):
                self.panels['front']['image_index'] = index

            def __getattr__(self, name):
                if name in ('set_transition', 'hide_text', 'set_info_scene',
                            'set_overlay_background', 'set_reactive_enabled',
                            'intense_transition_next', 'show_text', 'toggle_icon',
                            'set_reactive_preset', 'start_show', 'set_target',
                            'set_icon_motion', 'set_overlay_audio_reactivity',
                            'apply_scene'):
                    return lambda *args, **kwargs: None
                raise AttributeError(name)

        rt = FakeRuntime()
        output = io.StringIO()
        with patch.object(diagnostic.gc, 'mem_free', return_value=900000, create=True), \
                contextlib.redirect_stdout(output):
            tour = diagnostic.BoardDiagnostics(rt, [0, 1], None,
                                               stage_seconds=.03, startup_seconds=0)
            now = tour.ready_at
            for _ in range(len(tour.stages)):
                tour.tick(now)
                tour.profile('render/chaos', .001)
                tour.frame(now + .01)
                now = tour.current_started + .04
            tour.tick(now)
        names = [entry[1] for entry in tour.stages]
        self.assertIn('Chaos/trance', names)
        self.assertIn('Content/Fade', names)
        self.assertIn('Scene/Morph', names)
        self.assertIn('Text/Pixel', names)
        self.assertIn('Independent/two panels', names)
        self.assertEqual(output.getvalue().count('DIAG_STAGE '), len(tour.stages))
        self.assertIn('DIAG_DONE ', output.getvalue())
        self.assertTrue(rt.mirrored)
        self.assertEqual(rt.effect, 'Image')
        for line in output.getvalue().splitlines():
            if line.startswith('DIAG_STAGE '):
                self.assertIn('steady', json.loads(line[11:]))


if __name__ == '__main__':
    unittest.main()
