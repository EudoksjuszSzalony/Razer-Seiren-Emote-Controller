"""Developer Tools and shared icon behavior, without Tk display/USB hardware."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seiren_emote_gui import App
from windows_integration import apply_window_icon, configure_windows_app_identity, tray_image


class DeveloperToolsTests(unittest.TestCase):
    def test_developer_panel_defaults_closed_and_can_be_toggled(self):
        app = object.__new__(App)
        app.developer_tools_visible = False
        app.developer_controls = MagicMock()
        app.developer_button = MagicMock()
        App._toggle_developer_tools(app)
        self.assertTrue(app.developer_tools_visible)
        app.developer_controls.pack.assert_called_once_with(side='right')
        app.developer_button.configure.assert_called_with(text='Developer Tools ▴')
        App._toggle_developer_tools(app)
        self.assertFalse(app.developer_tools_visible)
        app.developer_controls.pack_forget.assert_called_once_with()
        app.developer_button.configure.assert_called_with(text='Developer Tools ▾')

    def test_window_icon_uses_static_tray_artwork(self):
        root = MagicMock()
        with patch('PIL.ImageTk.PhotoImage', side_effect=lambda x, **k: ('tk_image', x.size)) as mock:
            apply_window_icon(root)
        self.assertEqual(mock.call_count, 4)
        root.iconphoto.assert_called_once()
        args = root.iconphoto.call_args.args
        self.assertIs(args[0], True)
        self.assertEqual([i[1] for i in args[1:]], [(64,64), (48,48), (32,32), (16,16)])
        self.assertEqual(tray_image().size, (64, 64))
        self.assertEqual(len(root._seiren_window_icons), 4)

    def test_windows_identity_noop_other_platforms(self):
        with patch('windows_integration.sys.platform', 'linux'):
            self.assertIsNone(configure_windows_app_identity())
