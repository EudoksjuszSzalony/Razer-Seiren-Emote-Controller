"""Per-user Windows autostart plus optional system tray.

Tray callbacks occur on pystray's worker thread; GUI work is enqueued and
handled only by Tk's event loop.
"""
from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from typing import Callable

AUTOSTART_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
AUTOSTART_NAME = 'SeirenEmoteController'


def launch_command() -> str:
    """Quote either packaged EXE or Python GUI for HKCU Run."""
    if getattr(sys, 'frozen', False):
        parts = [sys.executable, '--tray']
    else:
        python = Path(sys.executable)
        if python.stem.lower() == 'python' and (python.with_name('pythonw.exe')).exists():
            python = python.with_name('pythonw.exe')
        parts = [str(python), str(Path(__file__).resolve().with_name('seiren_emote_gui.py')), '--tray']
    return subprocess.list2cmdline(parts)


def autostart_enabled() -> bool:
    if os.name != 'nt':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            value, _ = winreg.QueryValueEx(key, AUTOSTART_NAME)
            return isinstance(value, str) and value.strip() == launch_command()
    except FileNotFoundError:
        return False


def set_autostart(enabled: bool) -> None:
    if os.name != 'nt':
        raise RuntimeError('Autostart is available only on Windows.')
    import winreg
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY) as key:
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, launch_command())
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, AUTOSTART_NAME)
        except FileNotFoundError:
            pass


def tray_image():
    # Original generic green pixel icon; no proprietary Razer assets.
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (64, 64), (18, 22, 24, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((5, 5, 58, 58), radius=12, fill=(42, 53, 43, 255))
    pixels = [
        '..11....', '.1111...', '11.111..', '....11..',
        '....11..', '....11..', '....11..', '....11..',
    ]
    for y, row in enumerate(pixels):
        for x, pixel in enumerate(row):
            if pixel == '1':
                draw.rectangle((10 + x * 5, 10 + y * 5, 13 + x * 5, 13 + y * 5), fill=(89, 225, 55, 255))
    return image


class Tray:
    def __init__(self, command_queue: queue.Queue,
                 clear_exit_enabled: Callable[[], bool] | None = None):
        self.queue = command_queue
        self.clear_exit_enabled = clear_exit_enabled or (lambda: False)
        self.icon = None
        self.thread = None

    def start(self):
        import pystray
        if self.icon:
            return
        menu = pystray.Menu(
            pystray.MenuItem('Open', lambda *_: self.queue.put('open'), default=True),
            pystray.MenuItem(
                lambda _: 'Disable Autostart' if autostart_enabled() else 'Enable Autostart',
                lambda *_: self.queue.put('toggle_autostart'),
            ),
            pystray.MenuItem('Clear display on exit',
                             lambda *_: self.queue.put('toggle_clear_on_exit'),
                             checked=lambda _: self.clear_exit_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', lambda *_: self.queue.put('exit')),
        )
        self.icon = pystray.Icon('SeirenEmoteController', tray_image(), 'Seiren Emote Controller', menu)
        self.thread = threading.Thread(target=self.icon.run, name='SeirenTray', daemon=True)
        self.thread.start()

    def refresh(self):
        if self.icon:
            self.icon.update_menu()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None
