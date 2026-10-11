"""v0.3.7: first run defaults, new persistent toggles and tray queue actions."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seiren_emote_bridge as bridge


class Version037ConfigTests(unittest.TestCase):
    def test_new_install_orientation_and_preferences(self):
        with TemporaryDirectory() as temp:
            t = Path(temp)
            with patch.object(bridge, 'CONFIG', t / 'config.json'), patch.object(bridge, 'ROOT', t):
                cfg = bridge.read_config()
                self.assertEqual(cfg['transform'], 'flip_v')
                self.assertEqual(cfg['snake'], False)
                self.assertEqual(cfg['animated_only'], False)
                self.assertEqual(cfg['clear_on_exit'], False)
                self.assertEqual(cfg['animated_tray'], False)
                self.assertEqual(cfg['streamer_import_attempted'], False)
                cfg['animated_only'] = True
                cfg['clear_on_exit'] = True
                bridge.save_config(cfg)
                reloaded = bridge.read_config()
                self.assertIs(reloaded['animated_only'], True)
                self.assertIs(reloaded['clear_on_exit'], True)
                self.assertEqual(reloaded['transform'], 'flip_v')

    def test_v036_config_migration_keeps_old_settings_and_adds_new_booleans(self):
        with TemporaryDirectory() as temp:
            t = Path(temp)
            (t / 'config.json').write_text(json.dumps({
                'brightness': 0.35, 'speed': 1.75, 'transform': 'rotate90',
                'last_emote': '066_Fire.gif', 'animated_only': 'True',
                'clear_on_exit': 1,
            }), encoding='utf-8')
            with patch.object(bridge, 'CONFIG', t / 'sub' / 'config.json'), patch.object(bridge, 'ROOT', t):
                reloaded = bridge.read_config()
                self.assertEqual(reloaded['brightness'], 0.35)
                self.assertEqual(reloaded['speed'], 1.75)
                self.assertEqual(reloaded['last_emote'], '066_Fire.gif')
                self.assertEqual(reloaded['transform'], 'rotate90')
                self.assertIs(reloaded['animated_only'], False)
                self.assertIs(reloaded['clear_on_exit'], False)


if __name__ == '__main__':
    unittest.main()
