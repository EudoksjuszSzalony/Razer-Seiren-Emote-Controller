"""Check optional tray previews without launching a Windows notification icon."""
import sys
import queue
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from windows_integration import Tray, emote_tray_image

class DummyIcon:
    def __init__(self):
        self.icon = None

class TrayTests(unittest.TestCase):
    def test_preview_renders_source_pixels(self):
        source = Image.new('RGB', (8, 8))
        source.putpixel((0, 0), (255, 0, 0))
        image = emote_tray_image(source)
        self.assertEqual(image.size, (64, 64))
        self.assertEqual(image.getpixel((9, 9))[:3], (255, 0, 0))
        self.assertEqual(image.getpixel((20, 20))[:3], (0, 0, 0))

    def test_opt_in_throttled_and_static_fallback(self):
        active = False
        tray = Tray(queue.Queue(), animated_enabled=lambda: active)
        tray.icon = DummyIcon()
        blue = Image.new('RGB', (8, 8), 'blue')
        red = Image.new('RGB', (8, 8), 'red')
        with patch('windows_integration.time.monotonic', side_effect=[10.0, 10.05, 10.25]):
            tray.publish_frame(blue)
            self.assertIsNone(tray.icon.icon)
            active = True
            tray.publish_frame(blue)
            first = tray.icon.icon
            tray.publish_frame(red)
            self.assertIs(tray.icon.icon, first)
            tray.publish_frame(red, force=True)
            self.assertIsNot(tray.icon.icon, first)
        tray.restore_default_icon()
        self.assertEqual(tray.icon.icon.size, (64, 64))
