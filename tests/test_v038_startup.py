"""v0.3.8: resume the last selected emote in both GUI and tray launches."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seiren_emote_gui import App


class StartupTests(TestCase):
    def _app(self, name):
        app = object.__new__(App)
        app.config = {'last_emote': name}
        app.current_file = None
        app.select = MagicMock(return_value=True)
        app.status = MagicMock()
        return app

    def test_last_emote_is_restored(self):
        with TemporaryDirectory() as temp:
            target = Path(temp) / '066_Fire.gif'
            target.write_bytes(b'GIF89a')
            app = self._app('066_Fire.gif')
            with patch('seiren_emote_gui.EMOTES_DIR', Path(temp)):
                App._restore_last_emote(app)
            app.select.assert_called_once_with(target, silent=True)

    def test_no_file_leaves_app_usable(self):
        with TemporaryDirectory() as temp:
            app = self._app('file_not_found.gif')
            with patch('seiren_emote_gui.EMOTES_DIR', Path(temp)):
                App._restore_last_emote(app)
            app.select.assert_not_called()
            app.status.set.assert_called_once()

    def test_existing_user_selection_is_not_interrupted(self):
        app = self._app('066_Fire.gif')
        app.current_file = Path('123_other.gif')
        App._restore_last_emote(app)
        app.select.assert_not_called()

    def test_no_saved_selection_does_not_connect(self):
        app = self._app('')
        App._restore_last_emote(app)
        app.select.assert_not_called()

    def test_restoration_failure_shows_nonmodal_status(self):
        with TemporaryDirectory() as temp:
            target = Path(temp) / '066_Fire.gif'
            target.write_bytes(b'GIF89a')
            app = self._app('066_Fire.gif')
            app.select.return_value = False
            with patch('seiren_emote_gui.EMOTES_DIR', Path(temp)):
                App._restore_last_emote(app)
            app.status.set.assert_called_once()
