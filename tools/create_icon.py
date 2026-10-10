"""Generate a copyright-free 8-bit matrix icon for the Windows EXE/installer."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
path = root / 'build_assets' / 'app.ico'
path.parent.mkdir(parents=True, exist_ok=True)
icon = Image.new('RGBA', (256, 256), '#151b18')
draw = ImageDraw.Draw(icon)
draw.rounded_rectangle((14, 14, 242, 242), radius=48, fill='#293a30', outline='#63ce48', width=5)
pattern = [
    '..#.....',
    '.###....',
    '##.##...',
    '...##...',
    '...##...',
    '...##...',
    '...##...',
    '...##...',
]
for y, row in enumerate(pattern):
    for x, value in enumerate(row):
        if value == '#':
            x0, y0 = 32 + x * 24, 32 + y * 24
            draw.rounded_rectangle((x0, y0, x0 + 19, y0 + 19), radius=3, fill='#61e63c')
icon.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f'Created {path}')
