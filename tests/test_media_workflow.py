"""Startup importer, media watch and tray menu integration tests."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seiren_emote_gui import App


class LibraryWorkflowTests(unittest.TestCase):
    def test_first_run_import_only_once_when_library_empty(self):
        app = object.__new__(App)
        app.config = {'streamer_import_attempted': False}
        app.files = []
        app._persist = MagicMock()
        app._start_streamer_import = MagicMock()
        App._maybe_first_run_import(app)
        self.assertTrue(app.config['streamer_import_attempted'])
        app._start_streamer_import.assert_called_once_with(automatic=True)
        App._maybe_first_run_import(app)
        app._start_streamer_import.assert_called_once()

    def test_existing_library_skips_automatic_import(self):
        app = object.__new__(App)
        app.config = {'streamer_import_attempted': False}
        app.files = [Path('existing.gif')]
        app._persist = MagicMock()
        app._start_streamer_import = MagicMock()
        App._maybe_first_run_import(app)
        app._start_streamer_import.assert_not_called()

    def test_importer_results_refresh_library_on_main_thread(self):
        app = object.__new__(App)
        app._import_busy = True
        app.refresh_library = MagicMock()
        app.status = MagicMock()
        App._on_import_finished(app, 17, None, True)
        self.assertFalse(app._import_busy)
        app.refresh_library.assert_called_once()

    def test_directory_check_does_nothing_for_unchanged_files(self):
        app = object.__new__(App)
        app.closing = False
        app._media_snapshot = (('x.gif', 20, 1),)
        app.refresh_library = MagicMock()
        app.root = MagicMock()
        with patch('seiren_emote_gui.media_signature', return_value=app._media_snapshot):
            App._poll_media_directory(app)
        app.refresh_library.assert_not_called()
        app.root.after.assert_called_once()
