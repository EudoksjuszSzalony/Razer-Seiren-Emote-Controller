"""Orientation controls must cover every rotation and reflection exactly once."""
import unittest
from PIL import Image
from seiren_emote_bridge import (TRANSFORMS, DEFAULT_CONFIG,
                                 display_transform, display_controls, transform_frame)


class SimpleOrientationTests(unittest.TestCase):
    def test_all_saved_transforms_are_representable(self):
        result = {}
        for d in ('Up', 'Right', 'Down', 'Left'):
            for mirrored in (False, True):
                t = display_transform(d, mirrored)
                self.assertNotIn(t, result)
                result[t] = (d, mirrored)
                self.assertEqual(display_controls(t), (d, mirrored))
        self.assertEqual(set(result), set(TRANSFORMS))

    def test_known_physical_vertical_flip(self):
        self.assertEqual(display_controls('flip_v'), ('Down', True))
        self.assertEqual(display_transform('Down', True), 'flip_v')
        self.assertEqual(DEFAULT_CONFIG['transform'], 'flip_v')

    def test_calibration_covers_64_distinct_pixels(self):
        original = Image.new('RGB', (8, 8))
        for y in range(8):
            for x in range(8):
                original.putpixel((x, y), (x * 30, y * 25, x + y))
        for t in TRANSFORMS:
            transformed = transform_frame(original, t)
            self.assertEqual(len(set(transformed.getdata())), 64)

    def test_invalid_direction_rejected(self):
        with self.assertRaises(ValueError):
            display_transform('North-East', False)
        with self.assertRaises(ValueError):
            display_controls('banana')

if __name__ == '__main__':
    unittest.main()
