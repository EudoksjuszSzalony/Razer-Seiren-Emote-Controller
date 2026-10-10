import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seiren_hid import SeirenHidDevice

class FakeHID:
    def __init__(self): self.sent=[]
    def send_feature_report(self, p): self.sent.append(bytes(p)); return len(p)
    def close(self): pass

class TestHidTiming(unittest.TestCase):
    def test_pacing_and_report_order(self):
        fake=FakeHID()
        with patch.dict('os.environ', {'SEIREN_HID_ROW_DELAY_MS':'15'}), patch('seiren_hid.time.sleep') as sleep:
            device=SeirenHidDevice(fake)
            device.set_colors([(1,2,3)]*64)
            self.assertEqual([p[11] for p in fake.sent[:4]],list(range(4)))
            self.assertEqual(len(fake.sent),5)
            self.assertEqual(sleep.call_count,5)
            sleep.assert_any_call(0.015)
            device.set_colors([(1,2,3)]*64,delay_ms=35)
            sleep.assert_any_call(0.035)
            device.disconnect()
    def test_invalid_delay(self):
        with self.assertRaises(ValueError):
            SeirenHidDevice(FakeHID()).set_colors([(1,2,3)]*64,delay_ms=1000)

if __name__=='__main__': unittest.main()
