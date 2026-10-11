"""Media import and low-overhead library polling tests."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from media_library import import_user_media, media_signature


class MediaLibraryTests(unittest.TestCase):
    def test_import_duplicate_and_name_collision(self):
        with TemporaryDirectory() as root:
            p = Path(root)
            folder = p / 'library'
            first, second = p / 'A.png', p / 'source' / 'A.png'
            second.parent.mkdir()
            Image.new('RGB', (8, 8), 'green').save(first)
            Image.new('RGB', (8, 8), 'red').save(second)
            self.assertEqual(import_user_media([first], folder), (1, 0))
            self.assertEqual(import_user_media([first], folder), (0, 1))
            self.assertEqual(import_user_media([second], folder), (1, 0))
            self.assertEqual(sorted(x.name for x in folder.iterdir()), ['A.png', 'A_2.png'])

    def test_signature_detects_changes_without_decoding(self):
        with TemporaryDirectory() as root:
            p = Path(root)
            self.assertEqual(media_signature(p), ())
            img = p / 'image.gif'
            Image.new('RGB', (8, 8), 'blue').save(img)
            a = media_signature(p)
            self.assertEqual(a, media_signature(p))
            self.assertEqual(len(a), 1)
            (p / 'not-media.txt').write_text('x')
            self.assertEqual(a, media_signature(p))
            img.unlink()
            self.assertEqual(media_signature(p), ())

    def test_only_valid_png_or_gif_is_copied(self):
        with TemporaryDirectory() as root:
            p = Path(root)
            bad = p / 'fake.gif'
            bad.write_bytes(b'not a GIF')
            data = p / 'secret.txt'
            data.write_text('private')
            self.assertEqual(import_user_media([bad, data], p / 'emotes'), (0, 2))
            self.assertEqual(media_signature(p / 'emotes'), ())
