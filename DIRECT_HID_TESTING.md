# Experimental direct USB HID backend

**Status:** protocol-level implementation, not yet tested on physical hardware. The proven OpenRGB-based GUI v0.2 remains the working baseline and is not changed in this PR.

Seiren Emote USB identity: VID `1532`, PID `0F1B`; HID Usage Page `000C`, Usage `0001`. Only that interface is opened. Razer extended matrix uses **4 native rows of 16 RGB pixels**, each native row packing two visible 8-pixel rows, followed by one frame-apply report. The visible matrix remains 8×8. This corrects an earlier 8×8 HID report bug (dark alternating physical rows).

## Test on Windows (Windows PowerShell)

1. Close OpenRGB and disable Streamer Companion Chroma takeover. Keep Synapse 3 running if desired. Do **not** replace the Windows HID driver.
2. Install Python 3 and `py -m pip install -r requirements-hid.txt`.
3. Run `py hid_probe.py` to enumerate interfaces (**read-only**).
4. If exactly one matching lighting interface was reported, run `py -m unittest discover -s tests -v`, then `py hid_probe.py --test`.
5. Check whether the microphone displays red / green / blue vertical stripes. Report the PowerShell output, whether all visual rows illuminate with no dark gaps and whether Synapse 3 Studio remains unaffected.

No system changes, firmware writes, driver replacement or persistent device configuration are performed. Feature reports only target the expected microphone HID interface. The USB write mode is **explicit opt-in**.

## Next steps

- Wire up a selectable `direct-hid` / `openrgb` backend in the existing v0.2 GUI.
- Add frame pacing, reconnect handling, diagnostic logging and orientation calibration.
- Provide a **local-only** cache importer: find the existing installed Razer Streamer Companion application assets; parse and validate the embedded 8×8 GIF entries; import into the user's own app-data folder. Do not commit Razer artwork, other proprietary resources, or any application cache to this repository.
- Package with PyInstaller + Inno Setup (or another reproducible free Windows installer), Start-menu shortcut, uninstaller and optional startup-on-login through a user-level startup shortcut.

## Attribution and licensing

The USB packet format and VID/PID were researched against OpenRGB's RazerController and RazerDevices source, which marks those files `SPDX-License-Identifier: GPL-2.0-or-later`. The project itself is GPL-3.0, compatible with this usage. Retain upstream attribution in derived source modules. Original Razer artwork remains proprietary and is **not** licensed by this repository.

References:
- https://github.com/CalcProgrammer1/OpenRGB/blob/master/Controllers/RazerController/RazerController/RazerController.cpp
- https://github.com/CalcProgrammer1/OpenRGB/blob/master/Controllers/RazerController/RazerDevices.cpp
