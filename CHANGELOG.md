# Changelog

## v1.0.1 — 2026-10-11 (HID frame reliability fix)

- Increase the native Seiren Emote HID report pacing from 1 ms to **5 ms** by default. Testing on a physical microphone eliminated partial-color artifacts and intermittent frozen frames seen with animated `F_white` and rapid emote switching.
- Keep the existing 4×16 row transport, `Apply` report sequence, 8×8 calibration, animations, remembered emotes, and exit behavior unchanged. No extra black/clear frames are inserted when switching.
- Keep the `SEIREN_HID_ROW_DELAY_MS` environment override (0–250 ms) and explicit `delay_ms` override for diagnostics.
- Add a regression test for default 5 ms pacing and full report ordering.


## v1.0.0 — 2026-10-10 (first official stable release)

- Standalone Windows 10/11 x64 application with Direct USB HID support for the 8×8 Seiren Emote LED matrix; no OpenRGB server or separate Python installation is required.
- Designed to coexist with Synapse 3 and custom Chroma Studio effects on other devices.
- GIF/PNG playback with speed, brightness, and user-selected orientation; default vertical flip based on verified hardware mapping.
- Automatically resume the last selected emote and preferences on standard GUI and tray-only startup.
- Windows installer, Start Menu shortcut, autostart at login, tray menu, optional display clear on exit, and uninstall support.
- Import compatible emotes from the user's local Streamer Companion cache. Razer artwork is not redistributed.
- Free/open-source under GPL-3.0; installer unsigned and may trigger SmartScreen.

## v0.3.8 — installer preview

- Always restore the last saved emote after startup, including standard GUI launches and tray-only autostart. Previously this only happened with `--tray`.
- Startup no longer hides the only window when the system tray cannot initialize.
- Windows one-directory PyInstaller packaging, generated project icon and Inno Setup 6 installer with Start Menu entries, optional per-user autostart and clean uninstall.
- GitHub Actions Windows installer pipeline produces an unsigned setup EXE as a workflow artifact. No original Razer GIFs bundled.
- Preserve all v0.3.7 improvements: 4×16 HID, flip_v default, Apply playback resume, persistent brightness, speed, animation filter, and optional clear-on-exit.

## v0.3.7 Preview (2026-10-10)

- Fixed closing **Display Orientation** (Apply/Cancel): pause and resume the same cached GIF frames at the previous playback position. Immediately redraw the selected emote so the microphone never remains blank due to the calibration screen; falls back to the last saved emote if needed.
- Persist the **Animated only** filter to `%LOCALAPPDATA%\SeirenEmoteController\config.json`.
- Added a tray checkbox **Clear display on exit**, persisted in config. When enabled, an all-black frame is sent before closing the connected HID device. It is disabled by default; hiding the GUI never clears the display.
- Confirmed clean-install default orientation remains **flip_v** (Down + Mirror) based on the physical 8×8 mapping data.
- Fixed large unused space to the right of the emote library: column math matches actual cards and cards grow evenly to use canvas width. Supports significantly more columns on wide displays.
- Kept all GUI/tray/help strings in English. No proprietary Razer GIFs included.
- Added unit tests for first-run defaults and v0.3.6 config migration; GUI smoke tests with simulated HID on a virtual desktop.

## v0.3.6 Preview

- Four-way Display Orientation selector with optional horizontal mirror.
- Advanced clickable LED mapping and Direct USB HID 4×16 geometry support.
