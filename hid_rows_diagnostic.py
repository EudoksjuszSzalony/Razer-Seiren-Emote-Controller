#!/usr/bin/env python3
"""Razer Seiren Emote HID 4x16 geometry diagnostic (8x8 visual matrix).

Read-only operations until user confirms. Never use concurrently with OpenRGB.
We send 4 row packets of 16 RGB LEDs, not 8 packets of 8 RGB LEDs.
"""
import argparse
import time
from seiren_hid import SeirenHidDevice

BLACK = (0, 0, 0)
STRIPES = ((160, 0, 0), (180, 90, 0), (160, 160, 0), (0, 150, 0),
           (0, 160, 170), (0, 0, 160), (120, 0, 150), (160, 160, 160))


def colored_rows():
    return [STRIPES[y] for y in range(8) for _ in range(8)]


def main():
    parser = argparse.ArgumentParser(description='Seiren Emote 4x16 HID geometry test')
    parser.add_argument('--individual-rows', action='store_true',
                        help='After full-frame test, turn on every visual row one by one')
    parser.add_argument('--delay', type=float, default=1,
                        help='Milliseconds between native HID reports; default 1')
    args = parser.parse_args()
    if not 0 <= args.delay <= 250:
        parser.error('--delay must be between 0 and 250 ms')
    print('\nSEIREN EMOTE: 4x16 HID GEOMETRY TEST (VISIBLE 8x8)')
    print('USB transport: 4 HID rows of 16 pixels each, followed by one frame display command.')
    print('Close the previous GUI, OpenRGB and Streamer Companion. Synapse 3 may stay open.')
    input('Press Enter to display 8 colored stripes... ')
    device = SeirenHidDevice.connect()
    try:
        device.set_colors(colored_rows(), delay_ms=args.delay)
        input('Can you see 8 adjacent horizontal color stripes WITHOUT dark gaps?\n'
              'Take a photo if needed, then press Enter... ')
        if args.individual_rows:
            print('Testing individual VISIBLE rows 0..7:')
            for y in range(8):
                pixels = [STRIPES[y] if row == y else BLACK for row in range(8) for _ in range(8)]
                device.set_colors(pixels, delay_ms=args.delay)
                input(f'Only visible row {y} should be lit; Enter = next... ')
        # Clear pixels only after operator has seen output.
        device.set_colors([BLACK] * 64, delay_ms=args.delay)
    finally:
        device.disconnect()
    print('Test complete. If the stripes are continuous, test animations in the GUI.')

if __name__ == '__main__':
    main()
