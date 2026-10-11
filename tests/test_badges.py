"""README uses actual Shields.io SVG renders, guarded against invalid responses."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import update_readme_badges as badges


def mock_svg(label, message, color, **kwargs):
    # Unit tests must be offline. The release workflow checks real Shields.
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="20">'
            f'<title>{label}: {message}</title></svg>\n')


class BadgeTests(unittest.TestCase):
    def test_mirror_creates_valid_svgs_without_renegenerating_the_typography(self):
        with TemporaryDirectory() as tmp, patch.object(badges, 'shields_svg', side_effect=mock_svg):
            out = Path(tmp)
            badges.generate('v1.0.1', 12, out)
            self.assertEqual(len(list(out.glob('*.svg'))), 7)
            for path in out.glob('*.svg'):
                self.assertEqual(ET.parse(path).getroot().tag, '{http://www.w3.org/2000/svg}svg')
            self.assertIn('12', (out / 'downloads.svg').read_text())
            self.assertIn('v1.0.1', (out / 'release.svg').read_text())

    def test_native_style_options_and_hyphen_escaping(self):
        u = badges.shields_url('latest release', 'GPL-3.0', 'brightgreen')
        self.assertIn('latest%20release-GPL--3.0-brightgreen', u)
        self.assertIn('style=flat-square', u)
        self.assertIn('img.shields.io', u)

    def test_no_overwriting_on_failed_download(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            out.joinpath('downloads.svg').write_text('working original SVG')
            with patch.object(badges, 'shields_svg', side_effect=RuntimeError('unavailable')):
                with self.assertRaises(RuntimeError):
                    badges.generate('v1.0.1', 12, out)
            self.assertEqual(out.joinpath('downloads.svg').read_text(), 'working original SVG')
            self.assertEqual(len(list(out.iterdir())), 1)

    def test_release_stats_counts_published_assets(self):
        releases = [
            {'tag_name': 'v1.0.1', 'draft': False, 'prerelease': False,
             'assets': [{'download_count': 2}, {'download_count': 1}]},
            {'tag_name': 'v1.0.0', 'draft': False, 'prerelease': False,
             'assets': [{'download_count': 5}]},
            {'tag_name': 'v1.0.2-rc1', 'draft': False, 'prerelease': True,
             'assets': [{'download_count': 100}]},
        ]
        with patch.object(badges, 'api_get', side_effect=[releases, {'tag_name': 'v1.0.1'}]):
            self.assertEqual(badges.release_stats(), ('v1.0.1', 8))

    def test_negative_downloads_rejected_without_network(self):
        with TemporaryDirectory() as tmp:
            with patch.object(badges, 'shields_svg') as fetch:
                with self.assertRaises(ValueError):
                    badges.generate('v1.0.1', -1, Path(tmp))
                fetch.assert_not_called()
