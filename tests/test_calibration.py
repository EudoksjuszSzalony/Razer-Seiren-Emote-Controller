"""Pure tests for two-step calibration and all 8 matrix symmetries."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seiren_emote_bridge as bridge


class CalibrationTests(unittest.TestCase):
    def test_two_steps_can_correct_any_dihedral_orientation(self):
        plain = bridge.calibration_arrow(colored=False)
        colored = bridge.calibration_arrow(colored=True)
        for physical_orientation in bridge.TRANSFORMS:
            found_rotation = None
            for rotation in range(4):
                correction = bridge.calibration_transform(rotation, False)
                physical = bridge.transform_frame(
                    bridge.transform_frame(plain, correction), physical_orientation)
                if physical.tobytes() == plain.tobytes():
                    found_rotation = rotation
                    break
            self.assertIsNotNone(found_rotation, physical_orientation)
            # After the arrow points up, mirror toggle must match arm colors.
            possibilities = []
            for mirror in (False, True):
                correction = bridge.calibration_transform(found_rotation, mirror)
                physical = bridge.transform_frame(
                    bridge.transform_frame(colored, correction), physical_orientation)
                if physical.tobytes() == colored.tobytes():
                    possibilities.append(mirror)
            self.assertEqual(len(possibilities), 1, physical_orientation)

    def test_all_pixels_lit_in_static_row_diagnostic(self):
        im = bridge.calibration_row_test()
        values = bridge.rgb_image_to_values(im, 1.0, 'normal', False)
        self.assertEqual(len(values), 64)
        self.assertTrue(all(any(channel > 0 for channel in pixel) for pixel in values))
        self.assertEqual(len({tuple(values[y * 8]) for y in range(8)}), 8)
        for y in range(8):
            self.assertEqual(len(set(values[y * 8:(y + 1) * 8])), 1)

    def test_rotations_and_mirrors_are_unique(self):
        observed = [bridge.calibration_transform(r, f) for r in range(4) for f in (False, True)]
        self.assertEqual(len(set(observed)), 8)

if __name__ == '__main__':
    unittest.main()
