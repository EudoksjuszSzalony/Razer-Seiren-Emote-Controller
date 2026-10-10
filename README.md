# Razer Seiren Emote Controller — v1.0.0

A small **Windows 10/11** application that plays PNG and animated GIF emotes on the **Razer Seiren Emote's 8×8 RGB matrix** while your custom **Synapse 3 / Chroma Studio** profiles continue controlling other devices.

**Direct USB HID is the default backend; OpenRGB is not required.** The hardware controller and packaged Windows installer have been tested with a Seiren Emote on Windows 11.

## Installation (Windows 10/11 x64)

1. Download **`SeirenEmoteController_Setup_1.0.0.exe`** from the [v1.0.0 GitHub Release](https://github.com/EudoksjuszSzalony/Razer-Seiren-Emote-Controller/releases/tag/v1.0.0).
2. Quit OpenRGB and Streamer Companion if either controls the microphone; Synapse 3 can stay open for other devices.
3. Run the installer. Optionally enable **Start automatically when I sign in**; startup launches in the system tray and resumes the last emote.
4. Launch **Seiren Emote Controller** from the Windows Start Menu.
5. Click **Import Emotes** to import GIFs from the local Streamer Companion cache, when available, or put your own GIF/PNG files into `%LOCALAPPDATA%\SeirenEmoteController\Emotes`.
6. Select an emote. It automatically resumes with saved brightness, speed, and orientation on subsequent launches.

> The installer is **not digitally signed**, so Windows SmartScreen may warn about an unfamiliar app. Verify the download came from this project's Releases page. Razer's copyrighted GIFs are **not** bundled.

## Run from source (developers)

Python 3.11+:

```powershell
py -m pip install -r requirements.txt
py seiren_emote_gui.py
```

## Display orientation (simple)

Click **Display Orientation** on the main toolbar. You will see the expected green arrow (RED on the LEFT, BLUE on the RIGHT). Click the **Up / Right / Down / Left** buttons to rotate the output. Check **Mirror horizontally** if needed. Your microphone updates instantly; press **Apply** to save, or **Cancel** to keep the old setting. The most recently selected animation resumes immediately after either action (without reloading the GIF).

For the device mapping confirmed with physical measurements in October 2026, the correction is **`flip_v`**, represented in this GUI as **Down + Mirror horizontally**. This is intentional: the controls represent the applied image transformation rather than the final arrow direction. Once applied, the **physical** arrow must point UP.

Settings (orientation, brightness, speed, last emote, Animated only, Clear display on exit, and backend) are stored in `%LOCALAPPDATA%\SeirenEmoteController\config.json` and survive Windows restarts.

## Advanced calibration

The **Advanced calibration / LED mapping** link is at the bottom of the Display Orientation window; most people will never need it. It shows **one bright orange pixel** against a near-black background at a time. Click its corresponding position on the left-to-right / top-to-bottom 8×8 grid. Do not enter any coordinate numbers. You can skip or retry uncertain readings, export the mapping as JSON, or confirm a recommended correction only after visually checking the arrow. Repeated clicks produce a nonblocking warning instead of a popup.

## Background mode and Windows

Run `py seiren_emote_gui.py --tray` to start without a window and resume the last emote. Double-click the tray icon or right-click **Open** to show the GUI. The tray menu also provides **Enable/Disable Autostart**, a persistent **Clear display on exit** checkbox (off by default), and **Exit**. With that checkbox enabled, the controller sends an all-black frame to the connected microphone before exiting. Closing the main GUI only hides it to the tray.

## Windows installer (no Python needed for end users)

The installer bundles the program, runtime, Direct HID support and optional OpenRGB fallback. It creates a Start Menu shortcut and uninstaller. During setup, opt into **Start automatically when I sign in** if desired. Login startup runs with `--tray`; the GUI stays hidden and the last saved emote automatically plays. You can change autostart later using the tray menu.

To build on Windows with **Python 3.12** and **Inno Setup 6** installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The generated installer appears in `release/SeirenEmoteController_Setup_1.0.0.exe`. The `.github/workflows/windows-installer.yml` GitHub Actions workflow builds it on Windows and attaches the installer to the matching GitHub Release when this version is merged to `main`.

**Windows SmartScreen:** unsigned community installers can trigger a warning. Download only from this repository and inspect the code; the installer is not code-signed.

**Updating/uninstalling:** settings and imported local GIFs remain in `%LOCALAPPDATA%\SeirenEmoteController` and are not deleted on uninstall. The autostart registry entry is removed when uninstalling. Close the existing controller before installing a newer version. Original Razer GIFs are never included in the installer.

## Library layout

The card grid now calculates columns using the **actual card width** (roughly 100 px instead of the former incorrect 124 px estimate). Columns stretch evenly to fill the available canvas. The Animated only filter is remembered between launches.

## Diagnostics and tests

The USB protocol uses VID `1532`, PID `0F1B`, HID Usage Page `000C`, Usage `0001`. The visible 8×8 image (64 pixels) is transmitted as four **native 16-pixel feature reports**, followed by a frame-apply report. This fixed alternating dark rows in the early driver.

Run `py -m unittest discover -s tests -v` for packet, orientation, importer and preferences checks. The standalone installer and Direct HID communication have been tested on Windows 11 with a Seiren Emote.

## License and third-party assets

Source code: GPL-3.0. The HID protocol was researched from OpenRGB's `RazerController` implementation (source files marked GPL-2.0-or-later): https://github.com/CalcProgrammer1/OpenRGB

Original Razer GIFs, Razer logos and proprietary Streamer Companion data are **not** included. Users may import resources already present on their own computers where permitted. This is a community project, not official Razer software.
