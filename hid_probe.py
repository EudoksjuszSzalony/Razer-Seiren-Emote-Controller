"""
Seiren Emote HID hardware smoke test.

Without --test: enumerate only, no USB writes.
With --test: send a single 8x8 color test image to the microphone.
Close OpenRGB / Streamer Companion control of the microphone first.
"""
from __future__ import annotations

import argparse
from seiren_hid import enumerate_interfaces, target_interfaces, SeirenEmoteHID


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only probe or direct HID LED test")
    parser.add_argument("--test", action="store_true", help="Send a low-brightness RGB test image")
    args = parser.parse_args()
    interfaces = enumerate_interfaces()
    print(f"Found {len(interfaces)} Seiren Emote HID interface(s):")
    for interface in interfaces:
        print(
            "  usage_page=0x%04X usage=0x%04X interface=%s"
            % (
                interface.get("usage_page") or 0,
                interface.get("usage") or 0,
                interface.get("interface_number", "?"),
            )
        )
    matches = target_interfaces()
    print(f"Matching lighting interfaces: {len(matches)}")
    if not args.test:
        print("Read-only mode: no USB writes. To test LED output, pass --test.")
        return
    if len(matches) != 1:
        raise SystemExit("No unique matching interface; refusing to send USB reports")
    print("Writing a static test frame; other Razer devices are not accessed.")
    pixels = []
    for y in range(8):
        for x in range(8):
            if x < 3:
                pixels.append((40, 0, 0))
            elif x < 5:
                pixels.append((0, 40, 0))
            else:
                pixels.append((0, 0, 40))
    with SeirenEmoteHID() as device:
        device.send_frame(pixels)
    print("USB write complete. Confirm the 3 colored vertical stripes on the microphone.")


if __name__ == "__main__":
    main()
