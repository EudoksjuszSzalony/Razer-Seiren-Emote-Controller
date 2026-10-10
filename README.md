# Seiren Emote Controller

Control the **Razer Seiren Emote** display with your own GIF and PNG emotes —  
without OpenRGB, and without taking over the rest of your Razer setup.

<p align="left">
  <img src="https://img.shields.io/github/downloads/EudoksjuszSzalony/Razer-Seiren-Emote-Controller/total?style=flat-square" alt="Downloads" />
  <img src="https://img.shields.io/github/v/release/EudoksjuszSzalony/Razer-Seiren-Emote-Controller?style=flat-square&label=Latest%20Release" alt="Latest Release" />
  <img src="https://img.shields.io/badge/No_Python_Required-Installer-2ea44f?style=flat-square&logo=windows&logoColor=white" alt="No Python required to install" />
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/github/license/EudoksjuszSzalony/Razer-Seiren-Emote-Controller?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/Status-Stable-success?style=flat-square" alt="Stable" />
</p>

---

## Download

[![Download for Windows](https://img.shields.io/badge/Download-Windows%20Installer-2ea44f?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/EudoksjuszSzalony/Razer-Seiren-Emote-Controller/releases/latest/download/SeirenEmoteController_Setup_Latest.exe)

**Windows 10/11 (x64)** · No Python or OpenRGB installation required.

[View all releases](https://github.com/EudoksjuszSzalony/Razer-Seiren-Emote-Controller/releases)

---

## What is this?

**Seiren Emote Controller** is a standalone Windows application for the  
**Razer Seiren Emote** microphone.

It lets you:

- play **animated GIFs**
- display **PNG emotes**
- keep using **Razer Synapse / Chroma Studio** for your other devices
- restore your **last played emote** automatically on startup
- run quietly in the **system tray**
- use a **native HID backend** without needing OpenRGB

---

## Features

- ✅ Native **Direct HID** control of the Seiren Emote LED matrix
- ✅ Works alongside **Synapse 3 / Chroma Studio**
- ✅ GIF and PNG playback
- ✅ Adjustable **brightness**
- ✅ Adjustable **animation speed**
- ✅ Easy **display orientation** controls
- ✅ Import emotes from local sources
- ✅ Tray mode + optional autostart
- ✅ Restore last selected emote on app launch
- ✅ Windows installer with Start Menu integration

---

## Quick Start

### 1. Install
Download the latest installer from the button above and run it.

### 2. Launch
Open **Seiren Emote Controller** from the Start Menu.

### 3. Connect
Click **Connect**.

### 4. Import emotes
Use **Import Emotes** or copy your own GIF/PNG files into the emotes folder.

### 5. Play
Click any emote in the library to display it on your Seiren Emote.

---

## Screenshots

### Main window
![Main UI](docs/screenshots/main-ui.png)

### Orientation setup
![Orientation](docs/screenshots/orientation.png)

### Example output on microphone
![Seiren Example](docs/screenshots/microphone-preview.png)

---

## Why this project?

The goal was to create a **simple, standalone controller** for the  
**Razer Seiren Emote** that:

- does **not** require OpenRGB for normal use
- does **not** break custom Synapse lighting on other devices
- is easy to install for non-technical users
- supports importing and playing emotes in a clean desktop app

---

## Notes

- The installer is currently **not digitally signed**.
  Windows SmartScreen may show a warning before launch.
- **Razer-owned original GIF assets are not redistributed** in this repository or release packages.
- This is an **independent community project** and is **not affiliated with Razer**.

---

## Build from source

Requires **Python 3.11+** (only for running from source, not for the Windows installer).

```powershell
py -m pip install -r requirements.txt
py seiren_emote_gui.py
```

---

## License

Licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See [LICENSE](LICENSE).

