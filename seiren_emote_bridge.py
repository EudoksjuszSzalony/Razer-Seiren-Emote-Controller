#!/usr/bin/env python3
"""Seiren Emote Controller: 8x8 GIF player with direct HID and optional OpenRGB.
Only changes Razer Seiren Emote. No interaction with Synapse or Tuya.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from PIL import Image, ImageOps

WIDTH = HEIGHT = 8
SUPPORTED = {'.gif', '.png', '.webp', '.bmp', '.jpg', '.jpeg'}
TRANSFORMS = ('normal', 'flip_v', 'flip_h', 'rotate180', 'rotate90', 'rotate270', 'transpose', 'transverse')
ROOT = Path(__file__).resolve().parent
from emote_importer import APP_DIR
CONFIG = APP_DIR / 'config.json'


def transform_frame(frame: Image.Image, transform: str) -> Image.Image:
    mapping = {
        'normal': None,
        'flip_v': Image.Transpose.FLIP_TOP_BOTTOM,
        'flip_h': Image.Transpose.FLIP_LEFT_RIGHT,
        'rotate180': Image.Transpose.ROTATE_180,
        'rotate90': Image.Transpose.ROTATE_90,
        'rotate270': Image.Transpose.ROTATE_270,
        'transpose': Image.Transpose.TRANSPOSE,
        'transverse': Image.Transpose.TRANSVERSE,
    }
    return frame if mapping[transform] is None else frame.transpose(mapping[transform])


def calibration_arrow(*, colored: bool = False) -> Image.Image:
    """Symmetric arrow for direction; red/blue wings for mirror calibration."""
    lines = ('...GG...', '..GGGG..', '.GGGGGG.', '...GG...',
             '...GG...', '...GG...', '...GG...', '...GG...')
    image = Image.new('RGB', (8, 8))
    for y, line in enumerate(lines):
        for x, value in enumerate(line):
            if value == 'G':
                color = (25, 220, 35)
                if colored and y in (1, 2):
                    if x < 3:
                        color = (255, 45, 25)
                    elif x > 4:
                        color = (35, 100, 255)
                image.putpixel((x, y), color)
    return image


def calibration_transform(rotation_steps: int, mirrored: bool) -> str:
    """Optional horizontal reflection then 0/90/180/270 degree CCW rotation."""
    if rotation_steps not in (0, 1, 2, 3):
        raise ValueError('Rotation steps must be 0..3')
    sentinel = Image.new('RGB', (8, 8))
    for y in range(8):
        for x in range(8):
            sentinel.putpixel((x, y), (x * 29, y * 30, (x + y) * 13))
    desired = transform_frame(sentinel, 'flip_h') if mirrored else sentinel
    for _ in range(rotation_steps):
        desired = transform_frame(desired, 'rotate90')
    for candidate in TRANSFORMS:
        if transform_frame(sentinel, candidate).tobytes() == desired.tobytes():
            return candidate
    raise RuntimeError('Unable to compose calibration transform')




DISPLAY_DIRECTIONS = {'Up': 0, 'Right': 3, 'Down': 2, 'Left': 1}

def display_transform(direction: str, mirror: bool) -> str:
    """Applied output orientation from the simple four-way controls."""
    if direction not in DISPLAY_DIRECTIONS:
        raise ValueError(f'Invalid direction: {direction!r}')
    return calibration_transform(DISPLAY_DIRECTIONS[direction], bool(mirror))


def display_controls(transform: str) -> tuple[str, bool]:
    """Recover UI radio/check states for a saved D4 transformation."""
    for mirrored in (False, True):
        for direction in DISPLAY_DIRECTIONS:
            if display_transform(direction, mirrored) == transform:
                return direction, mirrored
    raise ValueError(f'Unknown display transform: {transform!r}')

def calibration_row_test() -> Image.Image:
    """Eight static horizontal stripes illuminate every LED."""
    stripes = [(180, 0, 0), (180, 75, 0), (170, 170, 0), (0, 160, 10),
               (0, 100, 160), (0, 0, 180), (130, 0, 180), (170, 170, 170)]
    image = Image.new('RGB', (8, 8))
    for y, color in enumerate(stripes):
        for x in range(8):
            image.putpixel((x, y), color)
    return image


DEFAULT_CONFIG = {
    'transform': 'flip_v', 'brightness': 0.70, 'speed': 1.0,
    'snake': False, 'backend': 'hid', 'last_emote': '',
    'animated_only': False, 'clear_on_exit': False,
    'animated_tray': False, 'streamer_import_attempted': False,
}


def read_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    # v0.2 stored config beside its script. Migrate it once if needed.
    previous = ROOT / 'config.json'
    source = CONFIG if CONFIG.is_file() else previous
    if source.is_file():
        try:
            obj = json.loads(source.read_text(encoding='utf-8'))
            if isinstance(obj, dict):
                config.update({key: val for key, val in obj.items() if key in config})
        except (OSError, ValueError, TypeError):
            pass
    if config['transform'] not in TRANSFORMS:
        config['transform'] = DEFAULT_CONFIG['transform']
    for key, minimum, maximum in (('brightness', .10, 1.0), ('speed', .25, 3.0)):
        try:
            config[key] = min(maximum, max(minimum, float(config[key])))
        except (TypeError, ValueError):
            config[key] = DEFAULT_CONFIG[key]
    if config['backend'] not in ('hid', 'openrgb'):
        config['backend'] = 'hid'
    for key in ('animated_only', 'clear_on_exit', 'animated_tray', 'streamer_import_attempted'):
        if not isinstance(config.get(key), bool):
            config[key] = DEFAULT_CONFIG[key]
    return config


def save_config(cfg: dict):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG.with_suffix('.tmp')
    temporary.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(CONFIG)


def rgb_image_to_values(frame: Image.Image, brightness: float, transform: str, snake: bool):
    frame = frame.convert('RGBA')
    if frame.size != (8, 8):
        frame = frame.resize((8, 8), Image.Resampling.NEAREST)
    base = Image.new('RGBA', (8, 8), (0, 0, 0, 255))
    base.alpha_composite(frame)
    rgb = transform_frame(base.convert('RGB'), transform)
    px = rgb.load()
    rows = []
    for y in range(8):
        row = []
        for x in range(8):
            r, g, b = px[x, y]
            row.append((round(r * brightness), round(g * brightness), round(b * brightness)))
        if snake and y % 2:
            row.reverse()
        rows.extend(row)
    return rows


def get_frames(path: Path):
    """Returns PIL snapshots and durations; supports GIF disposal through Pillow seek."""
    with Image.open(path) as im:
        for n in range(getattr(im, 'n_frames', 1)):
            im.seek(n)
            duration_ms = im.info.get('duration', 100)
            yield im.convert('RGBA'), max(0.025, float(duration_ms or 100) / 1000)


def identify_emote_device(client):
    found = [d for d in client.devices if 'seiren emote' in d.name.lower()]
    if len(found) != 1:
        names = ', '.join(d.name for d in client.devices) or '(brak)'
        raise RuntimeError('Expected exactly one Seiren Emote device. Found: ' + names)
    dev = found[0]
    if len(dev.leds) != 64:
        raise RuntimeError(f'Found {len(dev.leds)} LEDs, expected 64.')
    return dev


def send_frame(device, rgb_cls, im, brightness, transform, snake):
    vals = rgb_image_to_values(im, brightness, transform, snake)
    device.set_colors([rgb_cls(*rgb) for rgb in vals], fast=True)
    return vals


def arrow_image():
    """Asymmetric arrow: green points upward, yellow dot left of its tail.
    Unique color marker distinguishes mirror vs rotation.
    """
    a = Image.new('RGB', (8, 8))
    pixels = [
        '...GG...',
        '..GGGG..',
        '.GGGGGG.',
        '...GG...',
        '...GG...',
        '...GG...',
        '.Y.GG...',
        '...GG...',
    ]
    for y, row in enumerate(pixels):
        for x, char in enumerate(row):
            if char == 'G':a.putpixel((x, y), (0, 255, 50))
            elif char == 'Y':a.putpixel((x, y), (255, 190, 0))
    return a


def orientation_descriptor(transform: str):
    """Predict observed head direction & yellow dot side for a transformed arrow."""
    marked = Image.new('RGB', (8, 8))
    marked.putpixel((3, 0), (1, 2, 3))  # tip
    marked.putpixel((3, 7), (3, 2, 1))  # tail
    marked.putpixel((1, 6), (5, 4, 3))  # side marker
    converted = transform_frame(marked, transform)
    pts = {}
    for y in range(8):
        for x in range(8):
            c = converted.getpixel((x, y))
            if c == (1, 2, 3):pts['tip'] = (x, y)
            if c == (3, 2, 1):pts['tail'] = (x, y)
            if c == (5, 4, 3):pts['dot'] = (x, y)
    dx=pts['tip'][0]-pts['tail'][0];dy=pts['tip'][1]-pts['tail'][1]
    direction = 'up' if dy < -1 else 'down' if dy > 1 else 'right' if dx>0 else 'left'
    mx=pts['dot'][0]-pts['tail'][0];my=pts['dot'][1]-pts['tail'][1]
    cross=dx*my-dy*mx
    side='left' if cross<0 else 'right'
    return direction,side


def inverse_transform(t: str) -> str:
    check = Image.new('RGB',(8,8))
    for y in range(8):
        for x in range(8):check.putpixel((x,y),(x*29,y*29,(x+y)*13))
    for inv in TRANSFORMS:
        if transform_frame(transform_frame(check,t),inv).tobytes() == check.tobytes():
            return inv
    raise RuntimeError('Could not invert display transformation')


def calibration(device, RGBColor, cfg: dict):
    arrow=arrow_image()
    print('\n=== SEIREN EMOTE DISPLAY CALIBRATION 8x8 ===')
    print('The GREEN arrow will remain visible until you respond.')
    print('The YELLOW dot identifies horizontal mirroring.')
    print('Look straight at the microphone, as you normally use it.')
    send_frame(device,RGBColor,arrow,1.0,'normal',cfg.get('snake',False))
    dmap={'u':'up','r':'right','d':'down','l':'left'}
    while True:
        d=input('Which way does the arrow point? [U]p / [R]ight / [D]own / [L]eft: ').strip().lower()
        if d in dmap:break
    print('Imagine you are walking in the direction of the arrow.')
    print('On which side is the yellow dot? Left or right?')
    while True:
        s=input('Is the yellow dot on the [L]eft or [R]ight? ').strip().lower()
        if s in ('l','r'):break
    seen=(dmap[d], 'left' if s=='l' else 'right')
    transforms={orientation_descriptor(t): t for t in TRANSFORMS}
    if seen not in transforms:
        raise RuntimeError('Display orientation did not match a supported rotation/reflection. Check --snake.')
    fix=inverse_transform(transforms[seen])
    send_frame(device,RGBColor,arrow,1.0,fix,cfg.get('snake',False))
    print(f'Selected correction: {fix}. The arrow should now point UP.')
    print('The yellow dot should be on the LEFT of the arrow tail.')
    ok=input('Does the display match? [Y/n]: ').strip().lower()
    if ok not in ('', 'y', 'yes'):
        print('Nothing saved. Run --calibrate again if needed.')
        return
    cfg['transform']=fix
    save_config(cfg)
    print(f'Saved settings to {CONFIG.name}. Playback will use this orientation automatically.')


def files_to_play(file_arg: str | None, folder_arg: str | None):
    if file_arg:
        p=Path(file_arg)
        if not p.is_absolute():p=Path.cwd()/p
        if not p.is_file() or p.suffix.lower() not in SUPPORTED:
            raise FileNotFoundError('Nie znaleziono wspieranego pliku: '+str(p))
        return [p]
    folder = Path(folder_arg) if folder_arg else ROOT/'Emotes'
    if not folder.is_absolute():folder=Path.cwd()/folder
    if not folder.is_dir():raise FileNotFoundError('Brak folderu: '+str(folder))
    ls=sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED)
    if not ls:raise FileNotFoundError('Nie znaleziono PNG/GIF w '+str(folder))
    return ls


def connect_backend(backend: str, port: int = 6742):
    if backend == 'hid':
        from seiren_hid import SeirenHidDevice, RGBColor
        dev = SeirenHidDevice.connect()
        return dev, RGBColor, dev
    if backend == 'openrgb':
        from openrgb import OpenRGBClient
        from openrgb.utils import RGBColor
        client = OpenRGBClient('127.0.0.1', port, 'Seiren Emote Controller')
        try:
            dev = identify_emote_device(client)
            dev.set_mode('Direct')
            return dev, RGBColor, client
        except Exception:
            client.disconnect()
            raise
    raise ValueError('Unknown backend: ' + backend)


def play(args):
    cfg=read_config()
    if args.transform:cfg['transform']=args.transform
    if args.brightness is not None:cfg['brightness']=args.brightness
    if args.snake:cfg['snake']=True
    if not 0<=cfg['brightness']<=1:raise ValueError('Brightness must be between 0 and 1')
    device, RGBColor, client=connect_backend(args.backend,args.port)
    try:
        if args.calibrate:
            calibration(device,RGBColor,cfg)
            return
        files=files_to_play(args.file,args.folder)
        print(f'Microphone: {device.name}; animations: {len(files)}; orientation: {cfg["transform"]}; brightness: {cfg["brightness"]}')
        print('Press Ctrl+C to stop. No other devices are controlled.')
        previous=None
        while True:
            for f in files:
                print('Odtwarzam',f.name)
                for frame,duration in get_frames(f):
                    started=time.monotonic()
                    values=rgb_image_to_values(frame,cfg['brightness'],cfg['transform'],cfg['snake'])
                    if previous!=values:
                        device.set_colors([RGBColor(*rgb) for rgb in values],fast=True)
                        previous=values
                    wait=max(duration/args.speed,1/args.max_fps)-(time.monotonic()-started)
                    if wait>0:time.sleep(wait)
            if args.once:break
    finally:
        try:client.disconnect()
        except Exception:pass


def main():
    p=argparse.ArgumentParser(description='Seiren Emote Controller - native HID or optional OpenRGB.')
    p.add_argument('--calibrate',action='store_true',help='Arrow orientation wizard, save to config.json')
    p.add_argument('--file',help='PNG/GIF filename')
    p.add_argument('--folder',help='PNG/GIF directory')
    p.add_argument('--once',action='store_true',help='Play once, do not loop')
    p.add_argument('--backend',choices=('hid','openrgb'),default='hid',help='Backend (default: USB HID)')
    p.add_argument('--port',type=int,default=6742,help='OpenRGB SDK port')
    p.add_argument('--transform',choices=TRANSFORMS,default=None,help='Override the display orientation from config.json')
    p.add_argument('--brightness',type=float,default=None,help='Brightness 0..1')
    p.add_argument('--speed',type=float,default=1.0,help='Animation speed multiplier')
    p.add_argument('--max-fps',type=float,default=20.0,help='Maximum frames per second')
    p.add_argument('--snake',action='store_true',help='Alternate row LED order (snake wiring)')
    args=p.parse_args()
    if args.speed<=0 or args.max_fps<1 or args.max_fps>60:p.error('speed >0, max-fps 1..60')
    try:play(args)
    except KeyboardInterrupt:print('\nPrzerwano.')
    except (OSError,RuntimeError,ValueError) as ex:
        print('Error:',ex,file=sys.stderr);sys.exit(1)


if __name__=='__main__':main()
