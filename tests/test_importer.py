import base64
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from io import BytesIO
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from emote_importer import extract_gifs, import_from_cache


def fake_gif(size=(8,8)):
    buf=BytesIO()
    Image.new('RGB',size,(10,20,30)).save(buf,format='GIF')
    return buf.getvalue()


class ImporterTests(unittest.TestCase):
    def test_filters_100px_previews(self):
        a,b=fake_gif(),fake_gif((100,100))
        blob=b'data:image/gif;base64,'+base64.b64encode(a)+b'---data:image/gif;base64,'+base64.b64encode(b)
        self.assertEqual(extract_gifs(blob),[a])

    def test_local_import(self):
        a=fake_gif()
        with TemporaryDirectory() as root:
            root=Path(root)
            (root/'module').write_bytes(b'data:image/gif;base64,'+base64.b64encode(a))
            n=import_from_cache(root,root/'emotes')
            self.assertEqual(n,1)
            self.assertEqual(next((root/'emotes').glob('*.gif')).read_bytes(),a)


if __name__=='__main__':
    unittest.main()
