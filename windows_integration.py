"""Per-user Windows autostart plus optional system tray.

Tray callbacks occur on pystray's worker thread; GUI work is enqueued and
handled only by Tk's event loop.
"""
from __future__ import annotations

import os
import sys
import ctypes
from pathlib import Path
import queue
import subprocess
import threading
import time
from typing import Callable

AUTOSTART_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
AUTOSTART_NAME = 'SeirenEmoteController'
# Keep identity stable across releases. Windows uses it to associate the
# taskbar button with our product rather than a generic python.exe process.
APP_USER_MODEL_ID = 'SeirenEmoteController.App'


def configure_windows_app_identity():
    """Must run before creating the first Tk window on Windows."""
    if sys.platform != 'win32':
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        # May be absent on restricted Windows environments.
        pass


def apply_window_icon(root):
    """Use the same static art as Tray, for title bar + Windows taskbar.

    iconphoto(default=True) also applies to subsequently created Toplevels.
    Retain Tk image references so garbage collection cannot remove the icon.
    """
    from PIL import Image, ImageTk
    original = tray_image()
    root._seiren_window_icons = [
        ImageTk.PhotoImage(original.resize((size, size), Image.Resampling.NEAREST), master=root)
        for size in (64, 48, 32, 16)
    ]
    root.iconphoto(True, *root._seiren_window_icons)



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
            # Match the actual Windows Run registration, not one exact quoting
            # convention (Inno Setup and list2cmdline may format it differently).
            return isinstance(value, str) and bool(value.strip())
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

def emote_tray_image(frame):
    """Render the current logical 8x8 emote in a 64px notification icon."""
    from PIL import Image, ImageDraw
    tile = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
    tile.alpha_composite(frame.convert('RGBA').resize((8, 8), Image.Resampling.NEAREST))
    img = Image.new('RGBA', (64, 64), (18, 22, 24, 255))
    ImageDraw.Draw(img).rounded_rectangle((5, 5, 58, 58), radius=12, fill=(26, 30, 33, 255))
    img.paste(tile.resize((48, 48), Image.Resampling.NEAREST), (8, 8))
    return img


class Tray:
    def __init__(self, command_queue: queue.Queue,
                 clear_exit_enabled: Callable[[], bool] | None = None,
                 animated_enabled: Callable[[], bool] | None = None):
        self.queue = command_queue
        self.clear_exit_enabled = clear_exit_enabled or (lambda: False)
        self.animated_enabled = animated_enabled or (lambda: False)
        self.icon = None
        self.thread = None
        self._last_icon_update = 0.0

    def start(self):
        import pystray
        if self.icon:
            return
        menu = pystray.Menu(
            pystray.MenuItem('Open', lambda *_: self.queue.put('open'), default=True),
            pystray.MenuItem('Autostart',
                             lambda *_: self.queue.put('toggle_autostart'),
                             checked=lambda _: autostart_enabled()),
            pystray.MenuItem('Clear display on exit',
                             lambda *_: self.queue.put('toggle_clear_on_exit'),
                             checked=lambda _: self.clear_exit_enabled()),
            pystray.MenuItem('Animated tray',
                             lambda *_: self.queue.put('toggle_animated_tray'),
                             checked=lambda _: self.animated_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', lambda *_: self.queue.put('exit')),
        )
        self.icon = pystray.Icon('SeirenEmoteController', tray_image(), 'Seiren Emote Controller', menu)
        self.thread = threading.Thread(target=self.icon.run, name='SeirenTray', daemon=True)
        self.thread.start()

    def publish_frame(self, frame, *, force=False):
        """Throttle icon redraws; do not add HID commands or a second timer."""
        if not self.icon or not self.animated_enabled():
            return
        now = time.monotonic()
        if not force and now - self._last_icon_update < 0.2:
            return
        self.icon.icon = emote_tray_image(frame)
        self._last_icon_update = now

    def restore_default_icon(self):
        self._last_icon_update = 0.0
        if self.icon:
            self.icon.icon = tray_image()

    def refresh(self):
        if self.icon:
            self.icon.update_menu()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None
