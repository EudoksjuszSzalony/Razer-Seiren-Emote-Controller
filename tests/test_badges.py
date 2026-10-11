"""Generated README badges should be valid SVGs with verified download counts."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import update_readme_badges as badges


class BadgeTests(unittest.TestCase):
    def test_valid_svg_and_no_remote_image_dependencies(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            badges.generate("v1.0.1", 12, path)
            self.assertEqual(len(list(path.glob("*.svg"))), 7)
            for asset in path.glob("*.svg"):
                doc = ET.parse(asset)
                self.assertTrue(doc.getroot().tag.endswith("svg"))
                self.assertNotIn("shields.io", asset.read_text())
            downloads = (path / "downloads.svg").read_text()
            self.assertIn("12", downloads)
            self.assertIn("downloads", downloads)
            self.assertIn("v1.0.1", (path / "release.svg").read_text())

    def test_release_stats_counts_published_assets(self):
        releases = [
            {"tag_name":"v1.0.1","draft":False,"prerelease":False,
             "assets":[{"download_count":2},{"download_count":1}]},
            {"tag_name":"v1.0.0","draft":False,"prerelease":False,
             "assets":[{"download_count":5}]},
            {"tag_name":"v1.0.2-rc1","draft":False,"prerelease":True,
             "assets":[{"download_count":100}]},
        ]
        with patch.object(badges, "api_get", side_effect=[releases, {"tag_name":"v1.0.1"}]):
            self.assertEqual(badges.release_stats(), ("v1.0.1", 8))

    def test_disallow_negative_downloads(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                badges.generate("v1.0.1", -1, Path(tmp))
