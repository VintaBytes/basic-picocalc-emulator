"""Four photograph modes and LCD geometry; no Qt needed."""
from pathlib import Path
from PIL import Image
from basic_cde.gui.skin_modern import (
    MODERN_SKINS, modern_skin_layout, stop_button_rect,
    modern_skin_asset_path, modern_key_zones, modern_key_at,
)

def test_four_skins_are_bundled_and_lcd_square():
    for mode,(photo,_,_) in MODERN_SKINS.items():
        path=Path(modern_skin_asset_path(mode))
        assert path.is_file(), f'Missing photograph: {path}'
        with Image.open(path) as im:
            assert im.size==photo
        layout=modern_skin_layout(mode)
        assert layout.screen_side==(640 if mode=='large' else 320)
        assert layout.screen_x+layout.screen_side<=layout.host_width
        assert layout.screen_y+layout.screen_side<=layout.host_height
        x,y,s=stop_button_rect(mode)
        assert 0<=x<layout.host_width
        assert 0<=y<layout.host_height
        assert s>=13

def test_key_hit_regions():
    for mode in ('horizontal','vertical'):
        zones=modern_key_zones(mode)
        for name in ('Q','F1','Up','Enter'):
            zone=next(z for z in zones if z.name==name)
            assert modern_key_at(zone.x+zone.width/2,
                                 zone.y+zone.height/2,mode)==name
    assert not modern_key_zones('large')
    assert not modern_key_zones('compact')


def test_final_photo_alignment():
    from basic_cde.gui.skin_modern import MODERN_SKINS
    assert MODERN_SKINS['vertical'][0] == (954, 1649)
    assert MODERN_SKINS['vertical'][1] == (88, 99, 710)
    assert MODERN_SKINS['horizontal'][1] == (98, 101, 700)


def test_vertical_1_to_1_and_photo_relative_keyboard():
    from basic_cde.gui.skin_modern import (
        MODERN_SKINS, modern_skin_layout, modern_key_at, modern_key_zones)
    from basic_cde.gui.skin_modern import modern_skin_asset_path
    from PIL import Image

    layout = modern_skin_layout('vertical')
    photo_w, photo_h = MODERN_SKINS['vertical'][0]
    x, y, aperture = MODERN_SKINS['vertical'][1]
    assert layout.screen_side == 320
    assert layout.screen_x == round(x * 320 / aperture)
    assert layout.screen_y == round(y * 320 / aperture)
    assert layout.host_width == round(photo_w * 320 / aperture)
    assert layout.host_height == round(photo_h * 320 / aperture)
    assert Image.open(modern_skin_asset_path('vertical')).size == (photo_w, photo_h)

    # El clic se convierte de píxeles de ventana a píxeles de fotografía.
    # Comprueba que en ambos espacios se identifica la misma tecla.
    scale_x = layout.host_width / photo_w
    scale_y = layout.host_height / photo_h
    for name in ('F1', 'Q', 'A', 'Space', 'Enter', 'Up', 'Down', 'Left', 'Right'):
        zone = next(z for z in modern_key_zones('vertical') if z.name == name)
        # Las flechas se prueban en su interior y no sobre su borde.
        corners = {
            'Up': (173, 855), 'Left': (112, 922),
            'Right': (236, 922), 'Down': (173, 978),
        }
        fx, fy = corners.get(name, (zone.x + zone.width / 2,
                                    zone.y + zone.height / 2))
        wx, wy = fx * scale_x, fy * scale_y
        assert modern_key_at(wx / scale_x, wy / scale_y, 'vertical') == name


def test_keyboardless_skins_v6_keep_integer_lcd_and_new_photo_sizes():
    from PIL import Image
    from basic_cde.gui.skin_modern import (MODERN_SKINS,
                modern_skin_asset_path, modern_skin_layout)
    cases = {
        'compact': ((1164,1216), (100,125,980), 320),
        'large': ((1203,1216), (47,74,1075), 640),
    }
    for mode, (photo_size, rect, side) in cases.items():
        assert MODERN_SKINS[mode][0] == photo_size
        assert MODERN_SKINS[mode][1] == rect
        with Image.open(modern_skin_asset_path(mode)) as im:
            assert im.size == photo_size
        layout = modern_skin_layout(mode)
        assert layout.screen_side == side
        assert layout.screen_x == round(rect[0] * side / rect[2])
        assert layout.screen_y == round(rect[1] * side / rect[2])
        assert layout.screen_x + side <= layout.host_width
        assert layout.screen_y + side <= layout.host_height
