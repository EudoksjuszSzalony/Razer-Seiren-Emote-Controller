import sys
from pathlib import Path
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import seiren_hid as d


class FakeHid:
    def __init__(self):
        self.packets=[]
        self.closed=False

    def send_feature_report(self, packet):
        self.packets.append(bytes(packet))
        return len(packet)

    def close(self):
        self.closed=True


class HidTests(unittest.TestCase):
    def test_report_layout(self):
        p=d.row_report(3, [(1, 2, 3)]*16)
        self.assertEqual(len(p), 91)
        self.assertEqual((p[0],p[2],p[6],p[7],p[8]),(0,0x3F,53,0x0F,0x03))
        self.assertEqual(p[9:14], bytes([0,0,3,0,15]))
        self.assertEqual(p[14:62],bytes([1,2,3]*16))
        self.assertEqual(p[89],__import__('functools').reduce(lambda x,y:x^y,p[3:89],0))
        a=d.apply_report()
        self.assertEqual((a[6],a[7],a[8]),(12,15,2))
        self.assertEqual(a[9:12], bytes([0,0,8]))

    def test_four_native_rows_and_apply(self):
        fake=FakeHid()
        device=d.SeirenHidDevice(fake)
        with mock.patch.object(d.time,'sleep'):
            device.set_colors([d.RGBColor(4,5,6)]*64)
        self.assertEqual(len(fake.packets),5)
        self.assertEqual([p[11] for p in fake.packets[:4]],list(range(4)))
        self.assertEqual(fake.packets[-1][7:9],bytes([15,2]))
        device.disconnect()
        self.assertTrue(fake.closed)

    def test_eight_logical_rows_pack_as_four_sixteen_pixel_reports(self):
        fake = FakeHid()
        device = d.SeirenHidDevice(fake)
        # All 8 visual rows have unique RGB: every native packet must contain
        # 8 pixels of the first row followed by 8 pixels of the second.
        with mock.patch.object(d.time, 'sleep'):
            device.set_colors([(y, 100 + y, 200 + y) for y in range(8) for _ in range(8)])
        self.assertEqual(len(fake.packets), 5)
        for native_y in range(4):
            report = fake.packets[native_y]
            self.assertEqual(report[6:9], bytes((53, 0x0F, 0x03)))
            self.assertEqual(report[9:14], bytes((0, 0, native_y, 0, 15)))
            rgb = report[14:14+48]
            self.assertEqual(rgb[:24], bytes((2*native_y, 100+2*native_y, 200+2*native_y))*8)
            self.assertEqual(rgb[24:], bytes((2*native_y+1, 101+2*native_y, 201+2*native_y))*8)
        device.disconnect()

    def test_native_row_validation(self):
        with self.assertRaises(ValueError):
            d.row_report(4, [(0,0,0)]*16)
        with self.assertRaises(ValueError):
            d.row_report(0, [(0,0,0)]*8)
        with self.assertRaises(ValueError):
            d.row_report(0, [(0,0,999)]*16)

    def test_invalid_pixel_count(self):
        with self.assertRaises(ValueError):
            d.SeirenHidDevice(FakeHid()).set_colors([(1,2,3)]*63)


if __name__=='__main__':
    unittest.main()
