import unittest
import json
from urllib.request import urlopen

import controller_ui


class ControllerUICompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = controller_ui.PHONE_HTML

    def assert_once(self, marker):
        self.assertEqual(
            self.html.count(marker),
            1,
            "expected exactly one %r in composed controller" % marker,
        )

    def test_build_starts_from_raw_base_document(self):
        self.assertNotIn('id="tabAudio"', controller_ui.BASE_CONTROLLER_HTML)
        self.assertNotIn('id="tabGuest"', controller_ui.BASE_CONTROLLER_HTML)
        self.assertNotIn('id="textMessage"', controller_ui.BASE_CONTROLLER_HTML)

    def test_foundation_transform_order_is_explicit(self):
        modules = [fn.__module__ for fn in controller_ui.CONTROLLER_TRANSFORMS[:4]]
        self.assertEqual(
            modules,
            [
                "audio_phone_server",
                "performance_phone_server",
                "controller_cleanup",
                "controller_state_ui",
            ],
        )

    def test_default_build_is_repeatable(self):
        first = controller_ui.build_controller_html()
        second = controller_ui.build_controller_html()
        self.assertEqual(first, second)
        self.assertEqual(first, controller_ui.PHONE_HTML)

    def test_foundation_sections_exist_once(self):
        for marker in (
            'id="tabAudio"',
            'id="textMessage"',
            'id="guest"',
            'id="quickPresetList"',
            "function startMic(){",
            "function renderLayerControls(){",
        ):
            self.assert_once(marker)

    def test_runtime_state_layer_is_applied_once(self):
        self.assert_once("function runtimeText(){")
        self.assert_once("function activeQuickMessage(){")

    def test_primary_performance_surfaces_exist_once(self):
        for marker in (
            'id="tabAudio"',
            'id="tabGuest"',
            'id="tabIcons"',
            'id="tabText"',
            'id="overlayIconGrid"',
            'id="intenseTransitionGrid"',
            'id="screenModeIndependent"',
            'id="screenModeLinked"',
            'id="scenes"',
        ):
            self.assert_once(marker)

    def test_info_scenes_and_background_controls(self):
        self.assertNotIn('data-info-scene="Weather"', self.html)
        self.assertIn('Clock + Weather', self.html)
        for marker in ('data-info-scene="Clock"',
                       'data-info-scene="Set Times"', 'data-info-scene="Waveform"',
                       'id="sceneSetTimes"', 'id="mirrorButton"',
                       'data-text-bg="Black"', 'data-icon-bg="Black"',
                       'data-clock-bg="Sky"', 'window.refreshTotemWeather=',
                       'data-schedule-day="2026-10-03"', 'America/Chicago'):
            self.assert_once(marker)

    def test_performance_navigation_and_setup_keep_controls_in_one_place(self):
        html = self.html
        self.assert_once('id="micButton"')
        self.assert_once('id="panelCard"')
        self.assert_once('id="targetCard"')
        self.assert_once('id="mirrorButton"')
        self.assertNotIn('id="sceneButtons"', html)
        self.assertNotIn('<h2>Performance Modes</h2>', html)
        self.assertLess(html.index('id="micButton"'), html.index('<div class="tabs">'))
        self.assertGreater(html.index('id="panelCard"'), html.index('<section id="edit"'))
        self.assertLess(html.index('id="panelCard"'), html.index('id="targetCard"'))
        self.assertLess(html.index('id="panelCard"'), html.index('id="mirrorButton"'))
        self.assertIn("[audio,icons,text,guest,tab('tabScenes')]", html)
        self.assertIn("if(mode==='Waveform'&&window.ensureLiveAudio", html)
        self.assertIn("id==='starter:pulse'", html)
        scenes = html.split('<section id="scenes"', 1)[1].split('</section>', 1)[0]
        self.assertLess(scenes.index('>Waveform</button>'), scenes.index('>Back to GIFs</button>'))
        self.assertNotIn('id="mirrorButton"', scenes)
        slideshow = html.split('<h2>Slideshow + Background Transitions</h2>', 1)[1].split('<h2>', 1)[0]
        self.assertIn('data-clock-bg="Black"', slideshow)

    def test_desktop_icon_previews_can_refresh_after_library_reload(self):
        previews = {"First": "data:image/png;base64,AAAA"}
        server = controller_ui.PhoneControlServer(0)
        server.set_icon_preview_provider(lambda: dict(previews))
        try:
            server.start()
            url = "http://127.0.0.1:%d/api/icon-previews" % server.server.server_address[1]
            with urlopen(url, timeout=2) as response:
                self.assertEqual(json.load(response), previews)
            previews["Added"] = "data:image/png;base64,BBBB"
            with urlopen(url, timeout=2) as response:
                self.assertEqual(json.load(response), previews)
        finally:
            server.stop()

    def test_controller_keeps_current_performance_language(self):
        self.assertIn("audio.textContent='Vibe'", self.html)
        self.assertIn("guest.textContent='Chaos'", self.html)
        self.assertIn('.tabs button.runtimeOn:after', self.html)
        self.assertNotIn("'Vibe ●'", self.html)
        self.assertIn('Full Scene → Next', self.html)
        self.assertIn('BACKGROUND MELT → NEXT', self.html)
        self.assertIn('Chill / Flow', self.html)

    def test_vibe_uses_musical_signal_language(self):
        for marker in (
            '>Energy<',
            '>Low<',
            '>Body<',
            '>Bright<',
            'Pulse sensitivity',
            'Low → Zoom',
            'Pulse → Flash',
            'Body → Hue',
            'Bright → Sparkles',
            'Energy → Brightness',
        ):
            self.assertIn(marker, self.html)
        self.assertIn('Silent — gate closed', self.html)
        self.assertIn('Reactive signals — fixed 0–100% scale', self.html)

    def test_vibe_presets_are_editable_without_sample_hits(self):
        for marker in (
            'id="myVibeButtons"',
            'id="vibePresetName"',
            'onclick="saveCurrentVibe()"',
            'onclick="addCurrentVibe()"',
            'onclick="removeMyVibe()"',
            'festivalTotem.vibePresets.v2',
            '>Shuffle</button>',
        ):
            self.assertIn(marker, self.html)
        self.assertNotIn('previewVibe(', self.html)
        self.assertNotIn('id="presetButtons"', self.html)

    def test_text_controls_are_simplified(self):
        self.assertIn('id="textAudioOff"', self.html)
        self.assertIn('id="textAudioSubtle"', self.html)
        self.assertIn('id="textAudioIntense"', self.html)
        self.assertIn("motion:'Static'", self.html)
        self.assertIn('speed:34', self.html)

    def test_batch_tagging_is_metadata_only(self):
        self.assertIn("cmd('batch_add_tag'", self.html)
        self.assertNotIn("await delay(18)", self.html)

    def test_compiled_document_is_complete(self):
        self.assertTrue(self.html.startswith('<!doctype html>'))
        self.assertTrue(self.html.rstrip().endswith('</html>'))
        self.assertEqual(self.html.lower().count('<!doctype html>'), 1)
        self.assertEqual(self.html.lower().count('</html>'), 1)
        self.assertIn('/api/state', self.html)
        self.assertIn('/api/command', self.html)
        self.assertGreater(len(self.html), 10000)


if __name__ == '__main__':
    unittest.main()
