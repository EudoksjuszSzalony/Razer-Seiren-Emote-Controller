# Changelog

## 0.3.8 — installer preview

- Always restore the last saved emote after startup, including standard GUI launches and tray-only autostart. Previously this only happened with `--tray`.
- Startup no longer hides the only window when the system tray cannot initialize.
- Windows one-directory PyInstaller packaging, generated project icon and Inno Setup 6 installer with Start Menu entries, optional per-user autostart and clean uninstall.
- GitHub Actions Windows installer pipeline produces an unsigned setup EXE as a workflow artifact. No original Razer GIFs bundled.
- Preserve all v0.3.7 improvements: 4×16 HID, flip_v default, Apply playback resume, persistent brightness, speed, animation filter, and optional clear-on-exit.

# Changelog

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
