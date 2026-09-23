import unittest

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
        ):
            self.assert_once(marker)

    def test_controller_keeps_current_performance_language(self):
        self.assertIn('>Vibe</button>', self.html)
        self.assertIn('>Chaos</button>', self.html)
        self.assertIn('Full Scene → Next', self.html)
        self.assertIn('BACKGROUND MELT → NEXT', self.html)
        self.assertIn('Chill / Flow', self.html)

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
        self.assertGreater(len(self.html), 10000)


if __name__ == '__main__':
    unittest.main()
