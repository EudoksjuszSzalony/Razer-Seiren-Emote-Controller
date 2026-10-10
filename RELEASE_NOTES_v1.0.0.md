# Seiren Emote Controller v1.0.0 — Official Release 🎉

First stable release of a standalone RGB 8×8 animated-emote controller for the **Razer Seiren Emote** microphone.

### Highlights

- **No OpenRGB required:** direct USB HID output with the validated native 4×16 packet layout, driving all 64 LEDs.
- **Works alongside Razer Synapse 3 / Chroma Studio** on your other Razer devices.
- **Animated GIF and PNG support:** adjustable playback speed and brightness, and easy display orientation controls.
- **Restore automatically:** remembers and plays your last selected emote after launching the GUI or signing in to Windows (tray-only startup).
- **Windows integration:** Start Menu shortcuts, optional autostart, notification-area controls, optional display clear on exit, and uninstaller.
- **Local importer:** optional import of compatible GIFs from your own installed Streamer Companion cache; bring your own PNG/GIF files as well.
- **No original Razer GIFs included** in the project or installer.

### Installation

Download **`SeirenEmoteController_Setup_1.0.0.exe`** below and run it on Windows 10/11 x64. Python and OpenRGB are not required.

Keep **Streamer Companion** and **OpenRGB** from simultaneously controlling the Seiren microphone; Synapse 3 may keep running to control your other devices.

The app stores its settings and locally imported emotes in `%LOCALAPPDATA%\SeirenEmoteController` and keeps them across upgrades and uninstall.

**Security note:** The installer is unsigned. Windows SmartScreen may warn about an unrecognized program. Download it from this GitHub Release and verify its origin.

**Licensing:** GPL-3.0, source available in this tagged repository snapshot. Razer and Seiren are trademarks of their respective owners; this is an independent community project, not affiliated with Razer.
