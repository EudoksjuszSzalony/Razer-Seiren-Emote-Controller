"""Pixel mapping logic tests, without microphone or graphical desktop."""
import unittest

from pixel_mapping import (DEFAULT_PROBE_POINTS, EXTRA_PROBE_POINTS,
                           physical_coordinate_after, infer_orientation)
from seiren_emote_bridge import TRANSFORMS, inverse_transform


class PixelMappingTests(unittest.TestCase):
    def test_all_eight_geometries_recovered_from_clicks(self):
        for orient in TRANSFORMS:
            observations = {idx: physical_coordinate_after(orient, idx)
                            for idx in DEFAULT_PROBE_POINTS}
            conclusion = infer_orientation(observations)
            self.assertEqual(conclusion['physical'], orient, conclusion)
            self.assertEqual(conclusion['correction'], inverse_transform(orient))

    def test_previous_duplicate_reports_are_not_silently_trusted(self):
        conclusions = infer_orientation({0: (0, 7), 8: (0, 7), 7: (7, 7), 15: (7, 7)})
        self.assertIsNone(conclusions['correction'])
        self.assertEqual(len(conclusions['duplicates']), 2)

    def test_skip_and_short_measurement(self):
        s = infer_orientation({0: (0, 7), 7: None, 8: None})
        self.assertEqual(s['count'], 1)
        self.assertIsNone(s['correction'])

    def test_no_silent_approximation_for_wrong_sample(self):
        samples = {i: physical_coordinate_after('flip_v', i) for i in DEFAULT_PROBE_POINTS}
        samples[8] = (4, 4)
        s = infer_orientation(samples)
        self.assertIsNone(s['correction'])
        self.assertEqual(s['candidates'], [])

    def test_physical_mapping_does_not_use_proprietary_assets(self):
        self.assertEqual(len(DEFAULT_PROBE_POINTS), 8)
        self.assertEqual(set(DEFAULT_PROBE_POINTS) & set(EXTRA_PROBE_POINTS), set())
        self.assertEqual(physical_coordinate_after('flip_v', 0), (0, 7))
        self.assertEqual(physical_coordinate_after('flip_v', 63), (7, 0))


if __name__ == '__main__':
    unittest.main()
