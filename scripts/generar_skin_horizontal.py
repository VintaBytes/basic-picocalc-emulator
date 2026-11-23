"""Genera una vista apaisada a partir de la foto de skin local.

No depende de MMBasic ni de archivos externos, solo de Pillow durante desarrollo.
La aplicación usa el PNG terminado y NO necesita Pillow.
"""
from pathlib import Path
from PIL import Image

ASSET = Path(__file__).resolve().parents[1] / 'src/basic_cde/gui/assets'
src = Image.open(ASSET / 'picocalc-transparent.png').convert('RGBA')
screen_crop = (45, 40, 785, 688)
keyboard_crop = (59, 690, 778, 1270)
keyboard_origin = (760, 35)
canvas = Image.new('RGBA', (1479, 648), (0, 0, 0, 0))
canvas.alpha_composite(src.crop(screen_crop), (0, 0))
canvas.alpha_composite(src.crop(keyboard_crop), keyboard_origin)
canvas.save(ASSET / 'picocalc-horizontal.png', optimize=True)
