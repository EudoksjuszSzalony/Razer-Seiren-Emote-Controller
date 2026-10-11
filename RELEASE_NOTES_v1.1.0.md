# Seiren Emote Controller v1.1.0 — Animated tray and media workflow

This release introduces quality-of-life features and a smoother Windows experience for the **Razer Seiren Emote** LED matrix.

### New and improved

- **Animated tray icon (optional)** — preview the currently playing emote directly in Windows notification area, capped at five updates per second. Original static icon remains available.
- **Clearer tray settings** — Autostart, Clear display on exit, and Animated tray use persistent checked menu items.
- **Automatic USB reconnection** — after unplugging and reconnecting the microphone, the app attempts to reconnect and resume the selected animated GIF or static image. Tested on physical hardware.
- **Connected / Disconnected indicator** — main toolbar shows connection state without additional HID traffic.
- **Cleaner everyday UI** — diagnostic Backend / Connect / Stop controls are under Developer Tools; Display Orientation stays accessible.
- **Media management** — Add PNG/GIF, Open media folder, Import Streamer Companion, Refresh icons.
- **First-run import and automatic library refresh** — best-effort background import from Streamer Companion's local cache if the library is empty, plus lightweight folder scans every five seconds.
- **Consistent Windows icon** for the EXE, taskbar, title bar and static tray.
- Updated README with guided Quick Start, screenshots, reliable repository-hosted Shields.io badges and developer-only source build instructions.

### Preserved behavior

- Tested default **5 ms** report spacing for the Seiren Emote HID firmware (v1.0.1 frame reliability fix).
- The 4×16 physical HID row transport followed by Apply, orientation calibration, saved settings, playback speed and brightness.
- No extra all-black frame between emotes. No OpenRGB requirement for native HID mode.

### Installation

Download **`SeirenEmoteController_Setup_1.1.0.exe`** for Windows 10/11 x64. The installer upgrades the existing installation, preserving local GIF/PNG files and preferences. Python and OpenRGB are not required for the installer.

This community GPL-3.0 installer is **unsigned** and may display a Microsoft SmartScreen warning. The project is not affiliated with Razer, and proprietary Razer images are not bundled.
