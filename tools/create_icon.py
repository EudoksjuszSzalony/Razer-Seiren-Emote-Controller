"""Generate a copyright-free Windows .ico from the app's static Tray icon.

One source of truth for the EXE, installer, title bar, taskbar and static Tray.
"""
from pathlib import Path
import sys
from PIL import Image

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from windows_integration import tray_image

output = root / 'build_assets' / 'app.ico'
output.parent.mkdir(parents=True, exist_ok=True)
source = tray_image().convert('RGBA')
icon = source.resize((256, 256), Image.Resampling.NEAREST)
icon.save(output, sizes=[(16, 16), (24, 24), (32, 32),
                         (48, 48), (64, 64), (128, 128), (256, 256)])
print(f'Created {output}')
