"""Pure protocol tests. No microphone or hidapi installation required."""
import unittest

from seiren_hid import make_report, frame_reports


class ReportTests(unittest.TestCase):
    def test_packet_shape(self):
        packet = make_report(0x0F, 0x03, bytes(range(29)))
        self.assertEqual(len(packet), 91)
        self.assertEqual(packet[0], 0)
        self.assertEqual(packet[2], 0x3F)
        self.assertEqual(packet[6:9], bytes((29, 0x0F, 0x03)))
        self.assertEqual(packet[9:38], bytes(range(29)))
        crc = 0
        for b in packet[3:89]:
            crc ^= b
        self.assertEqual(packet[89], crc)
        self.assertEqual(packet[90], 0)

    def test_four_native_rows_plus_apply(self):
        colors = [(x, y, 15) for y in range(8) for x in range(8)]
        packets = frame_reports(colors)
        self.assertEqual(len(packets), 5)
        for y, packet in enumerate(packets[:4]):
            self.assertEqual(packet[6:9], bytes((53, 0x0F, 0x03)))
            self.assertEqual(packet[9:14], bytes((0, 0, y, 0, 15)))
            self.assertEqual(packet[14:17], bytes((0, y * 2, 15)))
            self.assertEqual(packet[35:38], bytes((7, y * 2, 15)))
            self.assertEqual(packet[38:41], bytes((0, y * 2 + 1, 15)))
            self.assertEqual(packet[59:62], bytes((7, y * 2 + 1, 15)))
        self.assertEqual(packets[4][6:9], bytes((12, 0x0F, 0x02)))
        self.assertEqual(packets[4][11], 0x08)

    def test_rejects_invalid_frames(self):
        with self.assertRaises(ValueError):
            frame_reports([(0, 0, 0)])
        with self.assertRaises(ValueError):
            frame_reports([(0, 0, 256)] * 64)
        with self.assertRaises(ValueError):
            make_report(0x0F, 0x03, bytes(81))


if __name__ == "__main__":
    unittest.main()
