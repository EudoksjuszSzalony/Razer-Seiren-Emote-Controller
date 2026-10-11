# Seiren Emote Controller v1.0.1 — HID frame reliability fix

This maintenance release improves animation reliability on the **Razer Seiren Emote** LED matrix.

### Fixed

- **Partial-frame and mixed-color artifacts** while switching images or playing animated GIFs.
- **Intermittent held/frozen animation frames** caused by aggressive HID command pacing.
- The native HID backend now waits **5 ms between reports** (previously 1 ms). The 5 ms setting was tested on a physical Seiren Emote and the reported artifacts disappeared.

### Unchanged

- Same four 16-pixel HID rows followed by an Apply report; no new command queue and no black frame between images.
- Existing orientation, brightness, playback speed, saved emotes, startup/tray behavior, and installer settings.
- Optional `SEIREN_HID_ROW_DELAY_MS` override for troubleshooting.

### Install

Download **`SeirenEmoteController_Setup_1.0.1.exe`** on Windows 10/11 x64. Python and OpenRGB are not required. The installer upgrades the existing installation and preserves user settings and local emotes.

The installer is unsigned and Windows SmartScreen may display a warning. This is an independent GPL-3.0 community project and is not affiliated with Razer. Razer artwork is not bundled.
