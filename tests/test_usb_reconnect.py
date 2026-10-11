"""Unplug/replug recovery: static frames, active GIFs and background reconnect."""
import sys
import queue
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seiren_emote_gui import App

class USBReconnectTests(unittest.TestCase):
    def app(self):
        a = object.__new__(App)
        a.backend = MagicMock()
        a.backend.get.return_value = 'hid'
        a.root = MagicMock()
        a.queue = queue.Queue()
        a.status = MagicMock()
        a.connection_label = MagicMock()
        a.connection_text = MagicMock()
        a.device = a.client = a.rgb_cls = None
        a.current_file = None
        a.current_frames = []
        a.scheduled = None
        a.config = {'animated_tray': False, 'last_emote': ''}
        a.closing = False
        a._usb_probe_inflight = a._usb_connect_inflight = False
        a._usb_generation = 0
        a._next_usb_connect = 0.0
        a._reconnect_target = None
        a._persist = MagicMock()
        a.select = MagicMock(return_value=True)
        return a

    def test_disconnect_preserves_active_emote(self):
        app = self.app()
        app.current_file = Path('active.gif')
        app.device = app.client = MagicMock()
        App._on_usb_presence(app, False)
        self.assertEqual(app._reconnect_target, Path('active.gif'))
        self.assertIsNone(app.device)
        self.assertIsNone(app.current_file)
        app.connection_text.set.assert_called_with('● Disconnected')

    def test_replug_auto_restores_active_gif(self):
        app = self.app()
        app._reconnect_target = Path('active.gif')
        app._usb_generation = 3
        app._usb_connect_inflight = True
        h = (MagicMock(), MagicMock(), MagicMock())
        with patch.object(Path, 'is_file', return_value=True):
            App._on_usb_reconnect(app, 3, h, None)
        app.select.assert_called_once_with(Path('active.gif'), silent=True)
        self.assertIs(app.device, h[0])
        self.assertFalse(app._usb_connect_inflight)

    def test_replug_restores_last_static_image(self):
        app = self.app()
        app._usb_generation = 2
        app.config['last_emote'] = 'still.png'
        with patch('seiren_emote_gui.EMOTES_DIR', Path('gallery')):
            with patch.object(Path, 'is_file', return_value=True):
                App._on_usb_reconnect(app, 2, (MagicMock(), MagicMock(), MagicMock()), None)
        app.select.assert_called_once_with(Path('gallery/still.png'), silent=True)

    def test_stale_connect_result_gets_closed(self):
        app = self.app()
        app._usb_generation = 4
        h = (MagicMock(), MagicMock(), MagicMock())
        App._on_usb_reconnect(app, 3, h, None)
        h[2].disconnect.assert_called_once()
        self.assertIsNone(app.device)

    def test_enumeration_error_does_not_assume_unplug(self):
        app = self.app()
        app.device = MagicMock()
        App._on_usb_presence(app, None)
        self.assertIsNotNone(app.device)

    def test_connect_worker_is_nonblocking(self):
        app = self.app()
        with patch('seiren_emote_gui.threading.Thread') as thread:
            with patch('seiren_emote_gui.time.monotonic', return_value=10.0):
                App._on_usb_presence(app, True)
        self.assertTrue(app._usb_connect_inflight)
        thread.return_value.start.assert_called_once()
