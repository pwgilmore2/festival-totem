"""Validate staging, low-rate reporting and safe Wi-Fi credential reuse."""

import contextlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import termios
import threading
import time
import types
import unittest
from unittest.mock import MagicMock, patch

import matrixportal_diagnostics as diagnostic
from tools.run_matrixportal_diagnostics import collect, open_serial, private_program, probe_serial


class DiagnosticTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, 'openpty'), 'requires a Unix pseudoterminal')
    def test_probe_requires_board_bytes_before_deploy(self):
        master, slave = os.openpty()
        try:
            with self.assertRaises(TimeoutError):
                probe_serial(slave, seconds=.05)
            os.write(master, b'Performance: live\n')
            self.assertIn(b'Performance:', probe_serial(slave, seconds=.1))
        finally:
            os.close(master)
            os.close(slave)

    def test_serial_open_failure_explains_error(self):
        errors = []
        self.assertIsNone(open_serial('/no/such/usbmodem', errors))
        self.assertIn('FileNotFoundError', errors[0])

    def test_one_gif_transition_waits_for_presented_source_frames(self):
        rt = MagicMock()
        rt.base_effects = {'Rainbow': None}
        rt.icon_library.names.return_value = []
        rt.scenes = {}
        rt.panels = {'front': {'image_index': 0}, 'back': {'image_index': 0}}
        with patch.object(diagnostic.gc, 'mem_free', return_value=900000, create=True), \
                contextlib.redirect_stdout(io.StringIO()):
            tour = diagnostic.BoardDiagnostics(rt, [0], None, startup_seconds=0)
            tour.index = next(i for i, stage in enumerate(tour.stages) if stage[1] == 'Content/Fade')
            tour._enter('transition', 'Fade')
            self.assertEqual(tour.pending, ('transition', 'Fade'))
            self.assertEqual(rt.set_effect.call_args.args, ('Rainbow',))
            tour.tick(tour.prepare_started + 1)
            self.assertEqual(tour.pending, ('transition', 'Fade'))
            tour.frame(tour.prepare_started + 1)
            tour.frame(tour.prepare_started + 1.1)
            tour.tick(tour.prepare_started + 1.2)
        self.assertIsNone(tour.pending)
        self.assertEqual(rt.set_effect.call_args.args, ('Image',))
        rt.set_transition.assert_any_call({'kind': 'Fade', 'duration': .65})
        self.assertEqual(tour.early.frames + tour.steady.frames, 0)

    def test_slow_stage_waits_for_frames_before_switching(self):
        rt = MagicMock()
        rt.base_effects = {'Rainbow': None}
        rt.icon_library.names.return_value = []
        rt.scenes = {}
        with patch.object(diagnostic.gc, 'mem_free', return_value=900000, create=True), \
                contextlib.redirect_stdout(io.StringIO()):
            tour = diagnostic.BoardDiagnostics(rt, [0], None, startup_seconds=0)
            tour.index = 0
            tour.current_started = time.monotonic()
            tour.early = diagnostic.PhaseStats()
            tour.steady = diagnostic.PhaseStats()
            tour.frame(tour.current_started + 2)
            tour.tick(tour.current_started + 6)
            self.assertEqual(tour.index, 0)
            tour.frame(tour.current_started + 7)
            tour.tick(tour.current_started + 13)
            self.assertEqual(tour.index, 1)

    @unittest.skipUnless(hasattr(os, 'openpty'), 'requires a Unix pseudoterminal')
    def test_serial_connection_asserts_dtr(self):
        master, slave = os.openpty()
        path = os.ttyname(slave)
        os.close(slave)
        try:
            with patch('tools.run_matrixportal_diagnostics.fcntl.ioctl') as ioctl, \
                    contextlib.redirect_stdout(io.StringIO()):
                descriptor = open_serial(path)
            self.assertIsNotNone(descriptor)
            os.close(descriptor)
            self.assertEqual(ioctl.call_args.args[1], termios.TIOCMBIS)
            self.assertEqual(ioctl.call_args.args[2],
                             struct.pack('I', termios.TIOCM_DTR))
        finally:
            os.close(master)

    @unittest.skipUnless(hasattr(os, 'openpty'), 'requires a Unix pseudoterminal')
    def test_unsupported_modem_ioctl_still_probes_serial(self):
        master, slave = os.openpty()
        path = os.ttyname(slave)
        os.close(slave)
        try:
            with patch('tools.run_matrixportal_diagnostics.fcntl.ioctl',
                       side_effect=OSError('unsupported')) as ioctl, \
                    contextlib.redirect_stdout(io.StringIO()):
                descriptor = open_serial(path)
            self.assertIsNotNone(descriptor)
            self.assertTrue(ioctl.called)
            os.close(descriptor)
        finally:
            os.close(master)

    @unittest.skipUnless(hasattr(os, 'openpty'), 'requires a Unix pseudoterminal')
    def test_serial_capture_keeps_boot_lines_and_stages(self):
        master, slave = os.openpty()
        def device():
            time.sleep(.05)
            os.write(master, b'Traceback on boot\nDIAG_BEGIN 1 / 1 GIF\n')
            os.write(master, b'DIAG_STAGE {"name":"GIF","status":"PASS","steady":{"fps":30,"p95_ms":34}}\n')
            os.write(master, b'DIAG_DONE {"stages":1,"slow_count":0}\n')
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / 'board.log'
            task = threading.Thread(target=device)
            task.start()
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    done, count = collect(log, None, 2, slave)
            finally:
                task.join()
                os.close(master)
            self.assertTrue(done)
            self.assertEqual(count, 1)
            self.assertIn('Traceback on boot', log.read_text())

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
                self.last_text = None

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

            def show_text(self, value=None):
                self.last_text = value

            def __getattr__(self, name):
                if name in ('set_transition', 'hide_text', 'set_info_scene',
                            'set_overlay_background', 'set_reactive_enabled',
                            'intense_transition_next', 'toggle_icon',
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
            self.assertIsNotNone(tour.finishing_at)
            self.assertFalse(tour.done)
            tour.frame(tour.finishing_at + .1)
            tour.frame(tour.finishing_at + .2)
            tour.tick(tour.finishing_at + 3.1)
        names = [entry[1] for entry in tour.stages]
        self.assertIn('Chaos/trance', names)
        self.assertIn('Content/Fade', names)
        self.assertIn('Scene/Morph', names)
        self.assertIn('Text/Pixel', names)
        self.assertIn('Independent/two panels', names)
        self.assertEqual(output.getvalue().count('DIAG_STAGE '), len(tour.stages))
        self.assertIn('DIAG_DONE ', output.getvalue())
        self.assertEqual(rt.last_text['message'], 'DONE')
        self.assertTrue(rt.mirrored)
        self.assertEqual(rt.effect, 'Image')
        for line in output.getvalue().splitlines():
            if line.startswith('DIAG_STAGE '):
                self.assertIn('steady', json.loads(line[11:]))


if __name__ == '__main__':
    unittest.main()
