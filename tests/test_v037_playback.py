"""Regression: orientation dialog must not abandon or reload running GIFs."""
from pathlib import Path
from unittest.mock import Mock
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seiren_emote_gui import App


class PlaybackResumeTests(unittest.TestCase):
    def test_pause_preserves_frame_state_and_resume_redraws(self):
        app = object.__new__(App)
        app.root = Mock()
        app.current_file = Path('/tmp/sample.gif')
        app.current_frames = [('image', 0.1)]
        app.frame_index = 0
        app.scheduled = 'running_timer'
        app.last_values = [(0, 0, 0)] * 64
        app.advance_frame = Mock()
        app.status = Mock()
        previous = App._pause_for_dialog(app)
        self.assertEqual(previous, Path('/tmp/sample.gif'))
        self.assertIsNone(app.scheduled)
        app.root.after_cancel.assert_called_once_with('running_timer')
        # The test does not create the file, so temporarily mock Path.is_file.
        from unittest.mock import patch
        with patch.object(Path, 'is_file', return_value=True):
            App._resume_after_dialog(app, previous)
        app.advance_frame.assert_called_once()
        self.assertIsNone(app.last_values)
        self.assertEqual(app.current_file, previous)
        self.assertEqual(len(app.current_frames), 1)

    def test_pause_recovers_last_saved_emote_if_not_currently_running(self):
        app = object.__new__(App)
        app.root = Mock()
        app.current_file = None
        app.current_frames = []
        app.scheduled = None
        app.config = {'last_emote': '066_Fire.gif'}
        from unittest.mock import patch
        with patch('seiren_emote_gui.EMOTES_DIR', Path('/tmp/Emotes')):
            with patch.object(Path, 'is_file', return_value=True):
                previous = App._pause_for_dialog(app)
        self.assertEqual(previous.name, '066_Fire.gif')

if __name__ == '__main__':
    unittest.main()
