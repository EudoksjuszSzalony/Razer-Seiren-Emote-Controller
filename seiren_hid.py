"""Minimal, Seiren Emote-only USB HID transport (no OpenRGB service needed).

Packet format documented by OpenRGB (GPL-2.0-or-later):
https://github.com/CalcProgrammer1/OpenRGB/tree/master/Controllers/RazerController
This module was written independently based on those device protocol details.
Do not open other Razer devices or the USB audio interface.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import time
from typing import Sequence

VID = 0x1532
PID = 0x0F1B
USAGE_PAGE = 0x000C
USAGE = 0x0001
REPORT_LENGTH = 91
TRANSACTION_ID = 0x3F
# The physical device is presented as an 8x8 image, but its Extended Matrix
# HID protocol accepts FOUR rows of SIXTEEN pixels (64 LEDs in both layouts).
# OpenRGB RazerDevices.cpp: seiren_emote_device rows=4, cols=16.
HID_ROWS = 4
HID_COLUMNS = 16
IMAGE_ROWS = 8
IMAGE_COLUMNS = 8


@dataclass(frozen=True)
class RGBColor:
    red: int
    green: int
    blue: int


def report(command_class: int, command_id: int, arguments: bytes, data_size: int | None = None) -> bytes:
    """Build one 91-byte Razer HID Feature Report (report_id=0)."""
    if len(arguments) > 80:
        raise ValueError('Razer HID arguments exceed 80 bytes')
    size = len(arguments) if data_size is None else data_size
    if not 0 <= size <= 80:
        raise ValueError('Invalid Razer HID data size')
    packet = bytearray(REPORT_LENGTH)
    packet[2] = TRANSACTION_ID
    packet[6] = size
    packet[7] = command_class
    packet[8] = command_id
    packet[9:9 + len(arguments)] = arguments
    checksum = 0
    for value in packet[3:89]:
        checksum ^= value
    packet[89] = checksum
    return bytes(packet)


def row_report(row: int, colors: Sequence[tuple[int, int, int]]) -> bytes:
    """One native 16-pixel row, containing two adjacent visual 8-pixel rows.

    No serpentine remapping here. The 8x8 image has already been flattened
    row-major by the caller, matching OpenRGB's 4x16 physical row transport.
    """
    if not 0 <= row < HID_ROWS or len(colors) != HID_COLUMNS:
        raise ValueError('Expected one of four HID rows containing 16 RGB pixels')
    if any(len(color) != 3 or any(not isinstance(v, int) or not 0 <= v <= 255 for v in color)
           for color in colors):
        raise ValueError('Each RGB color channel must be an integer in range 0..255')
    rgb = bytes(channel for pixel in colors for channel in pixel)
    return report(0x0F, 0x03, bytes((0, 0, row, 0, HID_COLUMNS - 1)) + rgb)


def apply_report() -> bytes:
    return report(0x0F, 0x02, bytes((0, 0, 8)) + bytes(9), data_size=12)


class SeirenHidDevice:
    name = 'Razer Seiren Emote'
    leds = tuple(range(64))

    def __init__(self, device):
        self._device = device
        self._lock = threading.Lock()
        self._closed = False
        # The Seiren Emote firmware may partially apply frames at 1 ms pacing.
        # 5 ms was validated on real hardware with GIF, hardcoded and full-screen
        # color tests. Keep the environment override for diagnostics.
        self.row_delay_ms = float(os.environ.get('SEIREN_HID_ROW_DELAY_MS', '5'))
        if not 0 <= self.row_delay_ms <= 250:
            raise ValueError('SEIREN_HID_ROW_DELAY_MS must be from 0 to 250')

    @classmethod
    def connect(cls):
        try:
            import hid
        except ImportError as exc:
            raise RuntimeError('Zainstaluj sterownik: py -m pip install hidapi') from exc
        matches = [item for item in hid.enumerate(VID, PID)
                   if item.get('usage_page') == USAGE_PAGE and item.get('usage') == USAGE]
        if len(matches) != 1:
            found = ', '.join(f"page={x.get('usage_page')} usage={x.get('usage')}" for x in hid.enumerate(VID, PID))
            raise RuntimeError('Nie znaleziono jednoznacznego interfejsu HID Seiren Emote '
                               '(usage page 0x0C, usage 1). Wykryto: ' + (found or 'brak'))
        device = hid.device()
        try:
            device.open_path(matches[0]['path'])
        except Exception as exc:
            raise RuntimeError('Could not open Seiren Emote interface. Close OpenRGB or disable microphone detection.') from exc
        return cls(device)

    def set_mode(self, mode):
        if mode != 'Direct':
            raise ValueError('Seiren HID supports only Direct mode')

    def _send(self, packet: bytes):
        sent = self._device.send_feature_report(packet)
        if sent != len(packet):
            raise OSError(f'Incomplete HID Feature Report ({sent}/{len(packet)} bytes)')

    def set_colors(self, colors, fast=True, *, delay_ms=None):
        if len(colors) != 64:
            raise ValueError('Seiren Emote requires 64 RGB colors')
        pixels = [(int(c.red), int(c.green), int(c.blue)) if hasattr(c, 'red')
                  else tuple(int(v) for v in c) for c in colors]
        if any(len(c) != 3 or any(not 0 <= v <= 255 for v in c) for c in pixels):
            raise ValueError('Colors must contain three values from 0 to 255')
        interval = self.row_delay_ms if delay_ms is None else float(delay_ms)
        if not 0 <= interval <= 250:
            raise ValueError('delay_ms must be from 0 to 250')
        with self._lock:
            if self._closed:
                raise RuntimeError('Device is closed')
            for y in range(HID_ROWS):
                self._send(row_report(y, pixels[HID_COLUMNS * y:HID_COLUMNS * (y + 1)]))
                if interval:
                    time.sleep(interval / 1000.0)
            self._send(apply_report())
            if interval:
                time.sleep(interval / 1000.0)

    def disconnect(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                self._device.close()
