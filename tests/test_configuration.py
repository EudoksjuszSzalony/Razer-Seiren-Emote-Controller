from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seiren_emote_bridge as bridge
from seiren_emote_gui import diagonal_arrow_image
from windows_integration import launch_command


class ConfigurationTests(unittest.TestCase):
    def test_defaults_and_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'config.json'
            with patch.object(bridge, 'CONFIG', path), patch.object(bridge, 'ROOT', Path(temp)):
                config = bridge.read_config()
                self.assertEqual(config['speed'], 1.0)
                config.update(brightness=.45, speed=2.25, last_emote='123_test.gif')
                bridge.save_config(config)
                restored = bridge.read_config()
                self.assertEqual(restored['brightness'], .45)
                self.assertEqual(restored['speed'], 2.25)
                self.assertEqual(restored['last_emote'], '123_test.gif')

    def test_clamp_untrusted_values(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'config.json'
            path.write_text('{"brightness":5,"speed":-7,"transform":"wrong"}')
            with patch.object(bridge, 'CONFIG', path), patch.object(bridge, 'ROOT', Path(temp)):
                cfg = bridge.read_config()
                self.assertEqual(cfg['brightness'], 1.0)
                self.assertEqual(cfg['speed'], .25)
                self.assertEqual(cfg['transform'], 'flip_v')

    def test_eight_unique_arrow_choices_and_inverses(self):
        image = diagonal_arrow_image()
        images = [bridge.transform_frame(image, name).tobytes() for name in bridge.TRANSFORMS]
        self.assertEqual(len(set(images)), 8)
        for observed in bridge.TRANSFORMS:
            corrected = bridge.transform_frame(bridge.transform_frame(image, observed),
                                               bridge.inverse_transform(observed))
            self.assertEqual(corrected.tobytes(), image.tobytes())

    def test_tray_startup_command(self):
        self.assertIn('--tray', launch_command())


if __name__ == '__main__':
    unittest.main()
