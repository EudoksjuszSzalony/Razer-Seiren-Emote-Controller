#!/usr/bin/env python3
"""Seiren Emote Controller v1.0.1 GUI + direct USB HID + Windows tray.

Copyright in program code: GPL-3.0. Original Razer images are not bundled.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

import seiren_emote_bridge as bridge
from emote_importer import APP_DIR, EMOTES_DIR, import_from_cache
from media_library import import_user_media, media_signature
from windows_integration import (Tray, autostart_enabled, set_autostart,
                                 configure_windows_app_identity, apply_window_icon)
from pixel_mapping import (DEFAULT_PROBE_POINTS, EXTRA_PROBE_POINTS, infer_orientation)

BG = '#181b1e'
SURFACE = '#292d30'
FG = '#edf0ee'
GREEN = '#51d037'
# Actual minimum including image, captions, inner/outer padding.
CARD_WIDTH = 100


def diagonal_arrow_image() -> Image.Image:
    """Asymmetric diagonal arrow: its 8 transforms are visually distinguishable."""
    image = Image.new('RGB', (8, 8))
    # Pointing north-east. The unequal-length wings make reflection detectable.
    dots = [(1, 6), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1),
            (5, 1), (4, 1), (3, 1), (6, 2), (6, 3)]
    for x, y in dots:
        image.putpixel((x, y), (50, 245, 65))
    return image


class App:
    def __init__(self, *, tray_only: bool = False):
        configure_windows_app_identity()
        self.root = tk.Tk()
        apply_window_icon(self.root)
        self.root.title('Seiren Emote Controller v1.0.1')
        self.root.geometry('1110x790')
        self.root.minsize(760, 540)
        self.root.configure(bg=BG)
        self.config = bridge.read_config()
        EMOTES_DIR.mkdir(parents=True, exist_ok=True)
        self.files = self._all_emote_files()
        self._media_snapshot = media_signature(EMOTES_DIR)
        self._import_busy = False
        self.developer_tools_visible = False
        self.client = self.device = self.rgb_cls = None
        self.scheduled = self.save_after = self.resize_after = None
        self.current_frames, self.current_file = [], None
        self.frame_index, self.last_values = 0, None
        self.image_refs = []
        self.grid_columns = 0
        self.queue = queue.Queue()
        self.tray = Tray(self.queue, clear_exit_enabled=lambda: bool(self.config.get('clear_on_exit', False)),
                         animated_enabled=lambda: bool(self.config.get('animated_tray', False)))
        self.search = tk.StringVar()
        self.only_animated = tk.BooleanVar(value=self.config.get('animated_only', False))
        self.brightness = tk.DoubleVar(value=self.config['brightness'])
        self.speed = tk.DoubleVar(value=self.config['speed'])
        self.backend = tk.StringVar(value=self.config['backend'])
        self.brightness_text = tk.StringVar()
        self.speed_text = tk.StringVar()
        self.status = tk.StringVar(value='Ready. Select an emote or import your local library.')
        self.preview_photo = None
        self._build_ui()
        self._update_controls()
        self.root.protocol('WM_DELETE_WINDOW', self.hide)
        self.render_grid()
        tray_ready = True
        try:
            self.tray.start()
        except Exception as exc:
            tray_ready = False
            self.status.set('System tray unavailable: ' + str(exc))
            # If the tray cannot start, do not hide the only window.
            self.root.protocol('WM_DELETE_WINDOW', self.exit)
        self.closing = False
        self.queue_after = self.root.after(100, self._check_queue)
        self.media_scan_after = self.root.after(5000, self._poll_media_directory)
        if tray_only and tray_ready:
            self.root.withdraw()
        else:
            self.root.deiconify()
        # Restore from the same saved profile regardless of how the app launches.
        # Defer until widgets, the tray, and the Tk event loop are initialized.
        self.root.after(600, self._restore_last_emote)
        self.root.after(1200, self._maybe_first_run_import)

    @staticmethod
    def _all_emote_files():
        return sorted((f for f in EMOTES_DIR.iterdir() if f.is_file()
                       and f.suffix.lower() in bridge.SUPPORTED), key=lambda f: f.name.casefold())

    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG, padx=14, pady=10)
        top.pack(fill='x')
        tk.Label(top, text='SEIREN EMOTE CONTROLLER', fg=GREEN, bg=BG,
                 font=('Segoe UI', 16, 'bold')).pack(side='left')
        self.developer_button = tk.Button(top, text='Developer Tools ▾',
                                         command=self._toggle_developer_tools,
                                         bg=SURFACE, fg=FG)
        self.developer_button.pack(side='right', padx=(7, 0))
        # Packed only on demand; avoids exposing diagnostic actions to new users.
        self.developer_controls = tk.Frame(top, bg=BG)
        tk.Button(self.developer_controls, text='Connect', command=self.connect,
                  bg='#336b24', fg='white', padx=12).pack(side='left', padx=(7, 0))
        tk.Label(self.developer_controls, text='Backend', bg=BG, fg=FG).pack(side='left', padx=(8, 3))
        backend_box = ttk.Combobox(self.developer_controls, textvariable=self.backend,
                                   values=['hid', 'openrgb'], state='readonly', width=8)
        backend_box.pack(side='left')
        backend_box.bind('<<ComboboxSelected>>', self._backend_changed)
        tk.Button(self.developer_controls, text='Stop', command=self.stop,
                  bg='#843a3a', fg=FG).pack(side='left', padx=(7, 0))
        tk.Button(top, text='Display Orientation', command=self.calibrate, bg=SURFACE,
                  fg=FG).pack(side='right', padx=(5, 0))

        library_actions = tk.Frame(self.root, bg=BG, padx=14, pady=5)
        library_actions.pack(fill='x')
        tk.Button(library_actions, text='Add PNG/GIF', command=self.add_media,
                  bg='#336b24', fg='white').pack(side='left', padx=(0, 7))
        tk.Button(library_actions, text='Open media folder', command=self.open_media_folder,
                  bg=SURFACE, fg=FG).pack(side='left', padx=(0, 7))
        tk.Button(library_actions, text='Import Streamer Companion', command=self.import_emotes,
                  bg=SURFACE, fg=FG).pack(side='left', padx=(0, 7))
        tk.Button(library_actions, text='Refresh icons', command=self.refresh_library,
                  bg=SURFACE, fg=FG).pack(side='left')

        controls = tk.Frame(self.root, bg=BG, padx=14, pady=5)
        controls.pack(fill='x')
        tk.Label(controls, text='Search:', fg=FG, bg=BG).pack(side='left')
        tk.Entry(controls, textvariable=self.search, width=22).pack(side='left', padx=(5, 10))
        self.search.trace_add('write', lambda *_: self.render_grid())
        tk.Checkbutton(controls, text='Animated only', variable=self.only_animated,
                       command=self._filter_changed, fg=FG, bg=BG, selectcolor=BG,
                       activebackground=BG, activeforeground=FG).pack(side='left')
        tk.Label(controls, text='Brightness', fg=FG, bg=BG).pack(side='left', padx=(12, 0))
        tk.Scale(controls, from_=0.1, to=1, resolution=0.05, variable=self.brightness,
                 command=self._slider_changed, orient='horizontal', length=115,
                 bg=BG, fg=FG, highlightthickness=0, showvalue=False).pack(side='left')
        tk.Label(controls, textvariable=self.brightness_text, fg=GREEN, bg=BG,
                 width=5, anchor='w').pack(side='left')
        tk.Label(controls, text='Speed', fg=FG, bg=BG).pack(side='left', padx=(8, 0))
        tk.Scale(controls, from_=0.25, to=3.0, resolution=0.25, variable=self.speed,
                 command=self._slider_changed, orient='horizontal', length=115,
                 bg=BG, fg=FG, highlightthickness=0, showvalue=False).pack(side='left')
        tk.Label(controls, textvariable=self.speed_text, fg=GREEN, bg=BG,
                 width=6, anchor='w').pack(side='left')

        self.count_label = tk.Label(self.root, text='', anchor='w', padx=14, bg=BG, fg='#aebbae')
        self.count_label.pack(fill='x')
        panel = tk.Frame(self.root, bg=BG)
        panel.pack(fill='both', expand=True, padx=14, pady=(5, 2))
        self.canvas = tk.Canvas(panel, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(panel, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.gridframe = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.gridframe, anchor='nw')
        self.gridframe.bind('<Configure>', lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self._canvas_resized)
        self.canvas.bind_all('<MouseWheel>', self._mouse_wheel)

        foot = tk.Frame(self.root, bg=BG, padx=14, pady=8)
        foot.pack(fill='x')
        self.preview = tk.Label(foot, bg='#000000', height=86, width=90)
        self.preview.pack(side='left', padx=(0, 12))
        tk.Label(foot, textvariable=self.status, anchor='w', justify='left', fg=FG,
                 bg=BG, wraplength=760).pack(side='left', fill='x', expand=True)

    def _toggle_developer_tools(self):
        """Reveal diagnostics on demand; independent of emote playback."""
        self.developer_tools_visible = not self.developer_tools_visible
        if self.developer_tools_visible:
            self.developer_controls.pack(side='right')
            self.developer_button.configure(text='Developer Tools ▴')
        else:
            self.developer_controls.pack_forget()
            self.developer_button.configure(text='Developer Tools ▾')

    def _filter_changed(self):
        self.config['animated_only'] = bool(self.only_animated.get())
        self._persist()
        self.render_grid()

    def _mouse_wheel(self, event):
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')

    def _canvas_resized(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)
        columns = max(1, (event.width - 6) // CARD_WIDTH)
        if columns != self.grid_columns:
            if self.resize_after is not None:
                self.root.after_cancel(self.resize_after)
            self.resize_after = self.root.after(110, self.render_grid)

    def _update_controls(self):
        self.brightness_text.set(f'{self.brightness.get() * 100:.0f}%')
        self.speed_text.set(f'{self.speed.get():.2f}×')

    def _slider_changed(self, _value=None):
        self._update_controls()
        if self.save_after is not None:
            self.root.after_cancel(self.save_after)
        self.save_after = self.root.after(300, self._persist)
        self.last_values = None  # Forces a redraw even for a static GIF frame.

    def _persist(self):
        self.save_after = None
        self.config.update({
            'brightness': round(float(self.brightness.get()), 2),
            'speed': round(float(self.speed.get()), 2),
            'backend': self.backend.get(),
            'animated_only': bool(self.only_animated.get()),
        })
        bridge.save_config(self.config)

    def render_grid(self):
        self.resize_after = None
        for widget in self.gridframe.winfo_children():
            widget.destroy()
        self.image_refs = []
        text = self.search.get().casefold().strip()
        filtered = []
        for file in self.files:
            if text and text not in file.stem.casefold():
                continue
            try:
                with Image.open(file) as im:
                    animated = getattr(im, 'n_frames', 1) > 1
            except (OSError, ValueError):
                continue
            if self.only_animated.get() and not animated:
                continue
            filtered.append(file)
        self.count_label.configure(text=f'Library: {len(filtered)} of {len(self.files)} emotes')
        cols = max(1, ((self.canvas.winfo_width() or 960) - 6) // CARD_WIDTH)
        old_cols = self.grid_columns
        self.grid_columns = cols
        # Stretch each column across the whole canvas and remove old grid column
        # weights after shrinking the window. The previous v0.3.6 hardcoded
        # 124px/column even though actual cards are about 96px wide.
        for col in range(max(old_cols, cols)):
            self.gridframe.grid_columnconfigure(col, weight=1 if col < cols else 0,
                                                uniform='emote_columns' if col < cols else '')
        if not filtered:
            tk.Label(self.gridframe, text='No emotes found. Click Import Emotes or copy GIF files into:\n' + str(EMOTES_DIR),
                     fg=FG, bg=BG, justify='left', pady=35).grid(row=0, column=0, sticky='w')
            return
        for i, file in enumerate(filtered):
            try:
                with Image.open(file) as im:
                    frames = getattr(im, 'n_frames', 1)
                    im.seek(min(frames - 1, 1 if frames > 1 else 0))
                    img = im.convert('RGBA').resize((72, 72), Image.Resampling.NEAREST)
            except (OSError, ValueError):
                # Files can change while being copied into the watched directory.
                continue
            photo = ImageTk.PhotoImage(img, master=self.root)
            self.image_refs.append(photo)
            cell = tk.Frame(self.gridframe, bg=SURFACE, padx=5, pady=6)
            cell.grid(row=i // cols, column=i % cols, padx=3, pady=4, sticky='nsew')
            stem = file.stem
            title = stem[4:].replace('_', ' ') if len(stem) > 4 and stem[:3].isdigit() else stem
            if len(title) > 15:
                title = title[:14] + '…'
            tk.Button(cell, image=photo, bg='black', activebackground='black', bd=0,
                      command=lambda f=file: self.select(f)).pack()
            tk.Label(cell, text=title, fg=FG, bg=SURFACE, width=13, font=('Segoe UI', 8)).pack()
            tk.Label(cell, text=f'{frames} frames' if frames > 1 else 'still image',
                     fg=GREEN if frames > 1 else '#8a9891', bg=SURFACE,
                     font=('Segoe UI', 8)).pack()

    def connect(self, *, silent=False):
        if self.device:
            return True
        try:
            self.device, self.rgb_cls, self.client = bridge.connect_backend(self.backend.get())
            self._persist()
            self.status.set(f'Connected: {self.backend.get().upper()} • Other Chroma devices remain in Synapse.')
            return True
        except Exception as exc:
            self.device = self.client = None
            self.status.set('Could not connect to Seiren Emote: ' + str(exc))
            if not silent:
                messagebox.showerror('Seiren Emote', str(exc) + '\n\nClose OpenRGB before using Direct HID on this microphone.')
            return False

    def _backend_changed(self, _event=None):
        self.stop()
        self._disconnect()
        self._persist()
        self.status.set('Backend switched to ' + self.backend.get() + '; select an emote.')

    def _disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        self.client = self.device = self.rgb_cls = None

    def select(self, file: Path, *, silent=False):
        if not file.is_file() or not self.connect(silent=silent):
            return False
        self.stop()
        try:
            self.current_frames = list(bridge.get_frames(file))
        except (OSError, ValueError) as exc:
            self.status.set('Could not open GIF: ' + str(exc))
            if not silent:
                messagebox.showerror('GIF Error', str(exc))
            return False
        if not self.current_frames:
            return False
        self.current_file = file
        self.frame_index, self.last_values = 0, None
        self.config['last_emote'] = file.name
        self._persist()
        self.status.set('Playing: ' + file.name)
        self.advance_frame()
        return True

    def advance_frame(self):
        self.scheduled = None
        if self.current_file is None or not self.current_frames:
            return
        frame, duration = self.current_frames[self.frame_index]
        try:
            values = bridge.rgb_image_to_values(frame, self.brightness.get(),
                                                self.config['transform'], self.config.get('snake', False))
            if values != self.last_values:
                self.device.set_colors([self.rgb_cls(*rgb) for rgb in values], fast=True)
                self.last_values = values
        except Exception as exc:
            self.stop()
            self.status.set('Frame transfer failed: ' + str(exc))
            self._disconnect()
            return
        image = frame.resize((80, 80), Image.Resampling.NEAREST)
        self.preview_photo = ImageTk.PhotoImage(image, master=self.root)
        self.preview.configure(image=self.preview_photo)
        if self.config.get('animated_tray', False):
            try:
                self.tray.publish_frame(frame)
            except Exception:
                pass  # A tray icon error must never interrupt HID playback.
        self.frame_index = (self.frame_index + 1) % len(self.current_frames)
        delay = max(50, round(duration * 1000 / max(0.25, self.speed.get())))
        self.scheduled = self.root.after(delay, self.advance_frame)

    def stop(self):
        if self.scheduled is not None:
            self.root.after_cancel(self.scheduled)
            self.scheduled = None
        self.current_file = None
        self.current_frames = []
        if self.config.get('animated_tray', False):
            try:
                self.tray.restore_default_icon()
            except Exception:
                pass

    def refresh_library(self):
        """Refresh directory view; never reimport assets."""
        self.files = self._all_emote_files()
        self._media_snapshot = media_signature(EMOTES_DIR)
        self.render_grid()

    def _poll_media_directory(self):
        """Watch filenames, sizes and mtimes only; avoid decoding idle GIFs."""
        if getattr(self, 'closing', False):
            return
        if media_signature(EMOTES_DIR) != self._media_snapshot:
            self.refresh_library()
        self.media_scan_after = self.root.after(5000, self._poll_media_directory)

    def add_media(self):
        selected = filedialog.askopenfilenames(parent=self.root,
                    title='Add PNG/GIF', filetypes=[('PNG and GIF', '*.png *.gif')])
        if not selected:
            return
        added, skipped = import_user_media(selected, EMOTES_DIR)
        self.refresh_library()
        self.status.set(f'Added {added} media file(s); {skipped} skipped.')
        if not added and skipped:
            messagebox.showwarning('Add PNG/GIF',
                'No new valid PNG/GIF files selected (invalid or duplicate).', parent=self.root)

    def open_media_folder(self):
        EMOTES_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(str(EMOTES_DIR))
            else:
                subprocess.Popen(['xdg-open', str(EMOTES_DIR)])
        except Exception as exc:
            messagebox.showerror('Media folder', str(exc), parent=self.root)

    def _maybe_first_run_import(self):
        """Import the local cache once on first launch if there are no emotes."""
        if self.config.get('streamer_import_attempted', False):
            return
        self.config['streamer_import_attempted'] = True
        self._persist()
        if not self.files:
            self._start_streamer_import(automatic=True)

    def _start_streamer_import(self, *, automatic=False, cache_root=None):
        if self._import_busy:
            return
        self._import_busy = True
        self.status.set('Searching local Streamer Companion cache...')
        def worker():
            try:
                count = import_from_cache(cache_root=cache_root)
                failure = None
            except Exception as exc:
                count, failure = 0, exc
            self.queue.put(('import_finished', count, failure, automatic))
        threading.Thread(target=worker, name='StreamerCacheImport', daemon=True).start()

    def import_emotes(self):
        """Explicit Streamer Companion import, independent of Refresh."""
        self._start_streamer_import()

    def _on_import_finished(self, count, failure, automatic):
        self._import_busy = False
        if failure is not None:
            if automatic:
                self.status.set('Streamer Companion cache unavailable. You can import it later.')
                return
            if isinstance(failure, (FileNotFoundError, RuntimeError)):
                folder = filedialog.askdirectory(parent=self.root,
                    title='Select Streamer Companion cache folder')
                if folder:
                    self._start_streamer_import(cache_root=Path(folder))
                return
            messagebox.showerror('Streamer Companion importer', str(failure), parent=self.root)
            return
        self.refresh_library()
        self.status.set(f'Imported {count} Streamer Companion emotes locally.')

    def _pause_for_dialog(self):
        """Stop the timer but preserve decoded GIF frames and the current index.

        Direct HID calibration writes are temporary. Keeping the playback data
        avoids the former blank-display behavior when closing the orientation
        dialog and prevents disk reload or a new device connection.
        """
        previous = self.current_file
        if previous is None:
            last = Path(self.config.get('last_emote', '')).name
            candidate = EMOTES_DIR / last if last else None
            previous = candidate if candidate and candidate.is_file() else None
        if self.scheduled is not None:
            self.root.after_cancel(self.scheduled)
            self.scheduled = None
        return previous

    def _resume_after_dialog(self, previous_emote: Path | None):
        """Redraw the last emote immediately with the current saved transform."""
        if previous_emote is None or not previous_emote.is_file():
            # No emote was available to resume; never leave the calibration
            # arrow on the microphone after the dialog has closed.
            try:
                self.device.set_colors([self.rgb_cls(0, 0, 0) for _ in range(64)], fast=True)
            except Exception:
                pass
            self.status.set('Display orientation updated. Select an emote to play.')
            return
        if previous_emote == self.current_file and self.current_frames:
            self.last_values = None  # Send frame again even if it is unchanged.
            self.advance_frame()
            self.status.set('Playing: ' + previous_emote.name)
        elif not self.select(previous_emote, silent=True):
            self.status.set('Could not resume the previous emote: ' + previous_emote.name)

    def calibrate(self):
        """Simple display orientation dialog; advanced LED probing is separate.

        The four arrow buttons apply an output rotation; Mirror flips horizontally.
        The physical microphone updates immediately, but settings are only saved
        on Apply. Closing the dialog restores the previous playback and settings.
        """
        if not self.connect():
            return
        previous_emote = self._pause_for_dialog()
        win = tk.Toplevel(self.root)
        win.title('Display Orientation')
        win.geometry('785x505')
        win.minsize(730, 465)
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()

        # The visible button represents the *applied image rotation*. This is
        # intentionally separate from the physical LED mapping underneath.
        saved_transform = self.config.get('transform', 'flip_v')
        saved_direction, saved_mirror = bridge.display_controls(saved_transform)
        direction_var = tk.StringVar(value=saved_direction)
        mirror_var = tk.BooleanVar(value=saved_mirror)
        state = {'closed': False, 'applied': False}
        status = tk.StringVar(value='Choose a direction and mirror setting until your microphone matches the preview.')

        tk.Label(win, text='DISPLAY ORIENTATION', bg=BG, fg=GREEN,
                 font=('Segoe UI', 16, 'bold')).pack(anchor='w', padx=23, pady=(20, 4))
        tk.Label(win, text='Adjust the output on your microphone. The preview below always shows the correct result.',
                 bg=BG, fg=FG, font=('Segoe UI', 10)).pack(anchor='w', padx=23, pady=(0, 14))
        content = tk.Frame(win, bg=BG)
        content.pack(fill='both', expand=True, padx=22)
        left = tk.Frame(content, bg=SURFACE, padx=18, pady=14)
        left.pack(side='left', anchor='n', padx=(0, 18))
        tk.Label(left, text='TARGET IMAGE', bg=SURFACE, fg=FG,
                 font=('Segoe UI', 11, 'bold')).pack(pady=(0, 10))
        example = bridge.calibration_arrow(colored=True).resize((224, 224), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(example, master=win)
        preview = tk.Label(left, image=photo, bg='black', bd=4)
        preview.image = photo
        preview.pack()
        tk.Label(left, text='Arrow UP • Red on LEFT • Blue on RIGHT', bg=SURFACE, fg=FG,
                 font=('Segoe UI', 9), wraplength=245).pack(pady=(12, 0))

        right = tk.Frame(content, bg=BG)
        right.pack(side='left', fill='both', expand=True)
        tk.Label(right, text='Rotate the output', bg=BG, fg=FG,
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(5, 8))
        buttons_frame = tk.Frame(right, bg=BG)
        buttons_frame.pack(anchor='w')
        direction_buttons = {}
        for row, entries in enumerate((('Up', 'Right'), ('Left', 'Down'))):
            for col, direction in enumerate(entries):
                labels = {'Up': '↑  Up', 'Right': '→  Right', 'Down': '↓  Down', 'Left': '←  Left'}
                button = tk.Button(buttons_frame, text=labels[direction], width=13, height=2,
                                   bg=SURFACE, fg=FG, command=lambda d=direction: choose(d))
                button.grid(row=row, column=col, padx=(0, 10), pady=(0, 9))
                direction_buttons[direction] = button
        tk.Checkbutton(right, text='Mirror horizontally', variable=mirror_var,
                       command=lambda: update_preview(), bg=BG, fg=FG,
                       selectcolor=SURFACE, activebackground=BG,
                       activeforeground=FG).pack(anchor='w', pady=(6, 10))
        tk.Label(right, textvariable=status, bg=BG, fg='#e1daa7',
                 justify='left', wraplength=350).pack(anchor='w', pady=(3, 12))
        advanced = tk.Label(right, text='Advanced calibration / LED mapping', fg='#98dbe9',
                            bg=BG, cursor='hand2', font=('Segoe UI', 9, 'underline'))
        advanced.pack(anchor='w', pady=(4, 0))

        footer = tk.Frame(win, bg=BG)
        footer.pack(fill='x', padx=23, pady=(12, 18))
        tk.Button(footer, text='Cancel', bg=SURFACE, fg=FG, width=14,
                  command=lambda: close()).pack(side='left')
        tk.Button(footer, text='Apply', bg='#336b24', fg='white', width=18,
                  command=lambda: apply()).pack(side='right')

        def current_transform():
            return bridge.display_transform(direction_var.get(), mirror_var.get())

        def update_preview():
            for direction, button in direction_buttons.items():
                button.configure(bg='#3b7832' if direction == direction_var.get() else SURFACE)
            try:
                bridge.send_frame(self.device, self.rgb_cls, bridge.calibration_arrow(colored=True),
                                  0.70, current_transform(), False)
                status.set('Does the microphone match the preview? Change rotation or Mirror if needed.')
            except Exception as exc:
                status.set('Could not update microphone: ' + str(exc))

        def choose(direction):
            direction_var.set(direction)
            update_preview()

        def close(*, open_advanced=False):
            if state['closed']:
                return
            state['closed'] = True
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()
            if open_advanced:
                self.root.after(30, self.pixel_mapping_gui)
            else:
                self._resume_after_dialog(previous_emote)

        def apply():
            self.config['transform'] = current_transform()
            self.config['snake'] = False
            self._persist()
            self.status.set('Display orientation saved: ' + self.config['transform'])
            state['applied'] = True
            close()

        advanced.bind('<Button-1>', lambda _event: close(open_advanced=True))
        win.protocol('WM_DELETE_WINDOW', close)
        update_preview()

    def pixel_mapping_gui(self):
        """Click physical LED positions; do not change saved transform until confirmed.

        Tests use raw USB logical pixels (no previous rotate/flip/snake).
        The photo-based observations can distinguish all 8 D4 orientations.
        """
        if not self.connect():
            return
        previous_emote = self._pause_for_dialog()
        win = tk.Toplevel(self.root)
        win.title('Advanced Calibration — LED Mapping')
        win.geometry('835x690')
        win.minsize(760, 620)
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()
        state = {
            'indices': list(DEFAULT_PROBE_POINTS),
            'ordinal': 0,
            'points': {},
            'pending': None,
            'closed': False,
        }
        status = tk.StringVar()
        sample = tk.StringVar()
        chosen = tk.StringVar(value='Select the glowing orange pixel on the grid.')
        recommendation = tk.StringVar()
        width = 336
        cell = 38
        origin = 16
        grid_wh = cell * 8

        tk.Label(win, text='ADVANCED LED MAPPING — CLICK THE LIT PIXEL',
                 fg=GREEN, bg=BG, font=('Segoe UI', 14, 'bold')).pack(pady=(16, 4))
        tk.Label(win, text='Face the microphone as you normally use it. Left, right, up and down are from your perspective. '
                 'Keep the microphone still during the test.',
                 fg=FG, bg=BG, wraplength=780, justify='center').pack(pady=(0, 12))
        body = tk.Frame(win, bg=BG)
        body.pack(fill='both', expand=True, padx=17)
        left = tk.Frame(body, bg=SURFACE, padx=12, pady=10)
        left.pack(side='left', padx=(0, 14), anchor='n')
        tk.Label(left, text='UP ↑', fg=GREEN, bg=SURFACE, font=('Segoe UI', 12, 'bold')).pack()
        map_canvas = tk.Canvas(left, bg='#101214', highlightthickness=0,
                               width=width, height=width, cursor='hand2')
        map_canvas.pack()
        tk.Label(left, text='LEFT ←     Physical LED Matrix     → RIGHT', fg=FG,
                 bg=SURFACE, font=('Segoe UI', 10, 'bold')).pack(pady=(5, 0))
        tk.Label(left, text='DOWN ↓', fg=GREEN, bg=SURFACE,
                 font=('Segoe UI', 12, 'bold')).pack(pady=(5, 0))
        tk.Label(left, textvariable=chosen, fg=FG, bg=SURFACE,
                 wraplength=336).pack(pady=(9, 0))
        right = tk.Frame(body, bg=BG)
        right.pack(side='left', fill='both', expand=True, anchor='n')
        tk.Label(right, textvariable=sample, fg=GREEN, bg=BG,
                 justify='left', wraplength=360, font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        tk.Label(right, text='Find the orange pixel on your microphone and click the same position on the grid.',
                 fg=FG, bg=BG, wraplength=350, justify='left').pack(anchor='w', pady=(12, 8))
        tk.Label(right, textvariable=recommendation, fg='#9de68f', bg=BG,
                 wraplength=350, justify='left').pack(anchor='w', pady=(10, 10))
        tk.Label(right, textvariable=status, fg='#eddaa5', bg=BG,
                 wraplength=350, justify='left').pack(anchor='w', pady=(6, 10))
        nav = tk.Frame(right, bg=BG)
        nav.pack(fill='x', pady=(20, 0))
        tk.Button(nav, text='← Back', bg=SURFACE, fg=FG,
                  command=lambda: navigate(-1)).pack(side='left', padx=(0, 6))
        tk.Button(nav, text='Skip', bg=SURFACE, fg=FG,
                  command=lambda: accept(skip=True)).pack(side='left', padx=6)
        tk.Button(right, text='Confirm →', bg='#386b27', fg='white',
                  height=2, command=lambda: accept(skip=False)).pack(fill='x', pady=(16, 8))
        tk.Button(right, text='Check 8 more pixels', bg=SURFACE, fg=FG,
                  command=lambda: extend()).pack(fill='x', pady=5)
        tk.Button(right, text='Export Mapping (JSON)', bg=SURFACE, fg=FG,
                  command=lambda: export_results()).pack(fill='x', pady=5)
        tk.Button(right, text='Preview and Apply Mapping', bg='#385b30', fg='white',
                  command=lambda: apply_orientation()).pack(fill='x', pady=(12, 0))
        footer = tk.Frame(win, bg=BG)
        footer.pack(fill='x', padx=20, pady=(12, 16))
        tk.Button(footer, text='Close / Resume Emote', bg=SURFACE, fg=FG,
                  command=lambda: close()).pack(side='right')

        def current_idx():
            return state['indices'][state['ordinal']]

        def redraw():
            map_canvas.delete('all')
            for y in range(8):
                for x in range(8):
                    selected = state['pending'] == (x, y)
                    map_canvas.create_rectangle(origin + cell*x + 2, origin + cell*y + 2,
                                                origin + cell*(x+1) - 2, origin + cell*(y+1) - 2,
                                                fill='#ff8c00' if selected else '#191b1d',
                                                outline='#ffe6b0' if selected else '#454a50',
                                                width=2 if selected else 1)
            if state['pending'] is not None:
                x, y = state['pending']
                chosen.set(f'Selected: {x + 1} from left, {y + 1} from top.')
            else:
                chosen.set('Click a grid cell matching the orange light, or Skip.')

        def on_click(event):
            x = (event.x - origin) // cell
            y = (event.y - origin) // cell
            if 0 <= x < 8 and 0 <= y < 8:
                state['pending'] = (x, y)
                redraw()

        map_canvas.bind('<Button-1>', on_click)

        def update_summary():
            result = infer_orientation(state['points'])
            recommendation.set(f"Measured {result['count']} pixel(s). " + result['message'])
            return result

        def show_current():
            i = current_idx()
            state['pending'] = state['points'].get(i)
            redraw()
            sample.set(f"Pixel {state['ordinal'] + 1} of {len(state['indices'])}")
            try:
                raw = [(0, 0, 0)] * 64
                raw[i] = (245, 110, 0)
                self.device.set_colors([self.rgb_cls(*rgb) for rgb in raw], fast=True)
                status.set('Only one orange pixel should be lit. Select it on the grid.')
            except Exception as exc:
                status.set('HID error: ' + str(exc))
            update_summary()

        def persist_json(destination=None):
            target_path = destination or (APP_DIR / 'seiren_pixel_mapping_results_v035.json')
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            result = infer_orientation(state['points'])
            data = {
                'probe_version': '0.3.5',
                'date': datetime.now().isoformat(timespec='seconds'),
                'coordinates': 'LEFT_to_RIGHT,UP_to_DOWN; 0..7; facing microphone',
                'native_hid_layout': '4x16',
                'logical_led_layout': '8x8',
                'results': {str(i): (None if pos is None else {'left_to_right': pos[0],
                                                              'up_to_down': pos[1]})
                            for i, pos in sorted(state['points'].items())},
                'inference': {
                    'physical': result['physical'],
                    'suggested_correction': result['correction'],
                    'duplicates': result['duplicates'],
                    'message': result['message'],
                }
            }
            target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                                   encoding='utf-8')
            return target_path

        def export_results():
            filename = filedialog.asksaveasfilename(parent=win,
                      title='Save LED mapping results', defaultextension='.json',
                      initialfile='seiren_pixel_mapping_results_v035.json',
                      filetypes=[('JSON', '*.json')])
            if filename:
                try:
                    saved = persist_json(filename)
                    status.set('Saved: ' + str(saved))
                except OSError as exc:
                    status.set('Could not save: ' + str(exc))

        def navigate(delta):
            new_ordinal = state['ordinal'] + delta
            if 0 <= new_ordinal < len(state['indices']):
                state['ordinal'] = new_ordinal
                show_current()

        def accept(*, skip):
            i = current_idx()
            pos = None if skip else state['pending']
            if pos is None and not skip:
                status.set('Select a pixel on the grid, or click Skip.')
                return
            if pos is not None:
                collisions = [other for other, loc in state['points'].items()
                              if other != i and loc == pos]
                if collisions:
                    status.set('This position was selected before. You can continue; double-check later if needed.')
            state['points'][i] = pos
            try:
                persist_json()
            except OSError as exc:
                status.set('Could not save mapping results: ' + str(exc))
            if state['ordinal'] < len(state['indices']) - 1:
                state['ordinal'] += 1
                show_current()
            else:
                state['pending'] = pos
                redraw()
                update_summary()
                status.set('Last point recorded. You can preview the suggested orientation, export results, or check more pixels.')

        def extend():
            if len(state['indices']) >= 16:
                status.set('All 16 sample pixels were checked.')
                return
            state['indices'].extend(EXTRA_PROBE_POINTS)
            state['ordinal'] = 8
            show_current()

        def apply_orientation():
            inferred = update_summary()
            transform = inferred['correction']
            if transform is None:
                messagebox.showwarning('Not enough information',
                    inferred['message'] + '\n\nCorrect a point or check 8 more pixels.', parent=win)
                return
            try:
                # Send a preview using the proposed transform; config untouched.
                bridge.send_frame(self.device, self.rgb_cls,
                                  bridge.calibration_arrow(colored=True),
                                  .70, transform, False)
            except Exception as exc:
                status.set('Could not display preview image: ' + str(exc))
                return
            confirmed = messagebox.askyesno('Confirm Display Orientation',
                'Does the arrow point UP with RED on the LEFT and BLUE on the RIGHT?\n\n'
                f'Detected physical transform: {inferred["physical"]}\n'
                f'Suggested correction: {transform}\n\n'
                'Yes = save orientation. No = keep previous settings.',
                parent=win)
            if confirmed:
                self.config['transform'] = transform
                self.config['snake'] = False
                self._persist()
                self.status.set('LED mapping orientation applied: ' + transform)
                close()
            else:
                show_current()

        def close():
            if state['closed']:
                return
            state['closed'] = True
            try:
                persist_json()
            except OSError:
                pass
            try:
                win.grab_release()
            except tk.TclError:
                pass
            win.destroy()
            self._resume_after_dialog(previous_emote)

        win.protocol('WM_DELETE_WINDOW', close)
        show_current()

    def _restore_last_emote(self):
        """Resume the last successful selection on every launch (GUI or tray)."""
        # Do not interrupt an emote picked by the user during startup.
        if self.current_file is not None:
            return
        last = self.config.get('last_emote')
        if not isinstance(last, str) or not last.strip():
            return
        target = EMOTES_DIR / Path(last).name
        if not target.is_file():
            self.status.set('Last emote is not installed. Import from Streamer Companion or choose another.')
            return
        if not self.select(target, silent=True):
            self.status.set(f'Could not restore {target.name}. Check the microphone connection.')

    def _check_queue(self):
        if getattr(self, 'closing', False):
            return
        try:
            while True:
                cmd = self.queue.get_nowait()
                if isinstance(cmd, tuple) and cmd[0] == 'import_finished':
                    self._on_import_finished(*cmd[1:])
                elif cmd == 'open':
                    self.show()
                elif cmd == 'toggle_autostart':
                    try:
                        enabled = not autostart_enabled()
                        set_autostart(enabled)
                        self.tray.refresh()
                        self.status.set('Autostart: ' + ('enabled' if enabled else 'disabled'))
                    except Exception as exc:
                        self.status.set('Autostart error: ' + str(exc))
                elif cmd == 'toggle_clear_on_exit':
                    self.config['clear_on_exit'] = not bool(self.config.get('clear_on_exit', False))
                    self._persist()
                    self.tray.refresh()
                    self.status.set('Clear display on exit: ' + ('enabled' if self.config['clear_on_exit'] else 'disabled'))
                elif cmd == 'toggle_animated_tray':
                    active = not bool(self.config.get('animated_tray', False))
                    self.config['animated_tray'] = active
                    self._persist()
                    self.tray.refresh()
                    try:
                        if active and self.current_frames:
                            index = (self.frame_index - 1) % len(self.current_frames)
                            self.tray.publish_frame(self.current_frames[index][0], force=True)
                        else:
                            self.tray.restore_default_icon()
                    except Exception:
                        pass
                    self.status.set('Animated tray: ' + ('enabled' if active else 'disabled'))
                elif cmd == 'exit':
                    self.exit()
                    return
        except queue.Empty:
            pass
        self.queue_after = self.root.after(100, self._check_queue)

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self._persist()
        self.root.withdraw()

    def exit(self):
        self.closing = True
        if getattr(self, 'media_scan_after', None) is not None:
            try:
                self.root.after_cancel(self.media_scan_after)
            except tk.TclError:
                pass
            self.media_scan_after = None
        if getattr(self, 'queue_after', None) is not None:
            try:
                self.root.after_cancel(self.queue_after)
            except tk.TclError:
                pass
            self.queue_after = None
        # This option affects only exiting the process via tray, not hiding
        # the main window. Do not touch a device that was never connected.
        if self.config.get('clear_on_exit', False) and self.device is not None:
            try:
                self.device.set_colors([self.rgb_cls(0, 0, 0) for _ in range(64)], fast=True)
            except Exception as exc:
                self.status.set('Unable to clear the microphone display: ' + str(exc))
        self.stop()
        if self.save_after is not None:
            self.root.after_cancel(self.save_after)
        self._persist()
        self._disconnect()
        self.tray.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tray', action='store_true', help='Start hidden with tray icon and last emote')
    args = p.parse_args()
    App(tray_only=args.tray).run()


if __name__ == '__main__':
    main()
