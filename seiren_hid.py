"""
Experimental direct USB HID backend for the Razer Seiren Emote (8 x 8 RGB).

Derived protocol information from OpenRGB's RazerController and RazerDevices:
https://github.com/CalcProgrammer1/OpenRGB
OpenRGB contributors, GPL-2.0-or-later; this adaptation GPL-3.0-or-later.
Only opens VID 1532 / PID 0F1B with Usage Page 000C / Usage 0001.
Not hardware-tested yet. Never run alongside OpenRGB or Streamer Companion
while both are trying to control the same microphone.
"""
from __future__ import annotations

import time
from typing import Iterable, Sequence

VID = 0x1532
PID = 0x0F1B
USAGE_PAGE = 0x000C
USAGE = 0x0001
TRANSACTION_ID = 0x3F
REPORT_LEN = 91
MATRIX_SIZE = 8


def _hid():
    try:
        import hid
    except ImportError as exc:
        raise RuntimeError("Missing HID dependency. Install with: py -m pip install hidapi") from exc
    return hid


def enumerate_interfaces() -> list[dict]:
    """Read-only; report all Seiren Emote HID interfaces."""
    return list(_hid().enumerate(VID, PID))


def target_interfaces() -> list[dict]:
    return [
        interface for interface in enumerate_interfaces()
        if interface.get("usage_page") == USAGE_PAGE
        and interface.get("usage") == USAGE
    ]


def make_report(command_class: int, command_id: int, arguments: bytes) -> bytes:
    """Pack a Razer extended matrix feature report including the checksum."""
    if not (0 <= command_class <= 255 and 0 <= command_id <= 255):
        raise ValueError("Command bytes must be in range 0..255")
    if len(arguments) > 80:
        raise ValueError("Razer feature report argument limit is 80 bytes")
    report = bytearray(REPORT_LEN)
    report[0] = 0x00  # HID report ID
    report[2] = TRANSACTION_ID
    report[6] = len(arguments)
    report[7] = command_class
    report[8] = command_id
    report[9:9 + len(arguments)] = arguments
    checksum = 0
    for value in report[3:89]:
        checksum ^= value
    report[89] = checksum
    return bytes(report)


def frame_reports(colors: Sequence[tuple[int, int, int]]) -> list[bytes]:
    """Return the 8 row packets and one 'show custom frame' packet.

    Colors are 64 RGB triples in row-major order. Orientation and brightness
    conversion belong to the GUI/image decoder, not this transport layer.
    """
    if len(colors) != 64:
        raise ValueError("Expected exactly 64 RGB pixels")
    for color in colors:
        if len(color) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in color):
            raise ValueError("Every pixel must contain three integer RGB channels in 0..255")
    reports = []
    for y in range(MATRIX_SIZE):
        rgb = bytes(channel for pixel in colors[y * 8:(y + 1) * 8] for channel in pixel)
        # Extended matrix arguments: [0,0,row,first_column,last_column,8*RGB]
        arguments = bytes((0, 0, y, 0, 7)) + rgb
        reports.append(make_report(0x0F, 0x03, arguments))
    # Extended matrix custom mode, effect 0x08.
    reports.append(make_report(0x0F, 0x02, bytes((0, 0, 0x08)) + bytes(9)))
    return reports


class SeirenEmoteHID:
    """Direct transport; writes ONLY to the Seiren Emote lighting interface."""

    def __init__(self, path: bytes | None = None, packet_delay: float = 0.001):
        self.path = path
        self.packet_delay = packet_delay
        self.device = None

    def open(self) -> "SeirenEmoteHID":
        if self.device is not None:
            return self
        matches = target_interfaces()
        if self.path is None:
            if len(matches) != 1:
                raise RuntimeError(
                    f"Expected one Seiren Emote LED interface, found {len(matches)}. "
                    "Run hid_probe.py to inspect USB interfaces."
                )
            path = matches[0]["path"]
        else:
            if self.path not in {entry["path"] for entry in matches}:
                raise RuntimeError("Requested HID path is not the Seiren Emote LED interface")
            path = self.path
        dev = _hid().device()
        try:
            dev.open_path(path)
        except Exception:
            dev.close()
            raise
        self.device = dev
        return self

    def close(self) -> None:
        if self.device is not None:
            try:
                self.device.close()
            finally:
                self.device = None

    def __enter__(self) -> "SeirenEmoteHID":
        return self.open()

    def __exit__(self, _type, _value, _traceback) -> None:
        self.close()

    def send_frame(self, colors: Sequence[tuple[int, int, int]]) -> None:
        if self.device is None:
            raise RuntimeError("HID device is not open")
        for report in frame_reports(colors):
            result = self.device.send_feature_report(report)
            if result != len(report):
                raise OSError(f"HID feature report failed: wrote {result} of {len(report)} bytes")
            if self.packet_delay > 0:
                time.sleep(self.packet_delay)
