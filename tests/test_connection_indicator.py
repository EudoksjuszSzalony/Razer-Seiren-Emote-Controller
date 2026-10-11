"""Regression tests for the passive main-window connection indicator.

The indicator reflects the backend handle owned by the application, not
live USB enumeration; it must not add commands to the 5 ms HID transport.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seiren_emote_gui import App, GREEN


class ConnectionIndicatorTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(App)
        app.connection_text = MagicMock()
        app.connection_label = MagicMock()
        app.device = app.client = app.rgb_cls = None
        app.status = MagicMock()
        app.backend = MagicMock()
        app.backend.get.return_value = 'hid'
        app._persist = MagicMock()
        return app

    def test_disconnected_by_default(self):
        app = self.make_app()
        App._update_connection_indicator(app)
        app.connection_text.set.assert_called_once_with('● Disconnected')
        app.connection_label.configure.assert_called_once_with(fg='#d9ae65')

    def test_successful_connection_updates_indicator(self):
        app = self.make_app()
        handle = MagicMock()
        pixel_cls = MagicMock()
        client = MagicMock()
        with patch('seiren_emote_gui.bridge.connect_backend',
                   return_value=(handle, pixel_cls, client)) as connect:
            self.assertTrue(App.connect(app, silent=True))
        connect.assert_called_once_with('hid')
        self.assertIs(app.device, handle)
        self.assertIs(app.client, client)
        app.connection_text.set.assert_called_with('● Connected')
        app.connection_label.configure.assert_called_with(fg=GREEN)
        self.assertTrue(App.connect(app, silent=True))
        connect.assert_called_once()  # No extra transport operation.

    def test_failed_connection_remains_disconnected(self):
        app = self.make_app()
        with patch('seiren_emote_gui.bridge.connect_backend',
                   side_effect=OSError('USB unavailable')):
            self.assertFalse(App.connect(app, silent=True))
        self.assertIsNone(app.device)
        self.assertIsNone(app.rgb_cls)
        app.connection_text.set.assert_called_with('● Disconnected')

    def test_disconnect_and_stop_are_distinct(self):
        app = self.make_app()
        app.device = MagicMock()
        app.client = MagicMock()
        app.rgb_cls = MagicMock()
        app.current_file = None
        app.current_frames = []
        app.scheduled = None
        app.config = {'animated_tray': False}
        App.stop(app)  # Stopping a GIF must not close the hardware handle.
        self.assertIsNotNone(app.device)
        App._disconnect(app)
        self.assertIsNone(app.device)
        app.connection_text.set.assert_called_with('● Disconnected')
        app.client is None
