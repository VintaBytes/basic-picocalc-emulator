from pathlib import Path

from basic_cde.gui.skin import (PHOTO_SIZE, PHOTO_SIZE_HORIZONTAL, SCREEN_RECT,
                                layout_for_mode, layout_for_screen, skin_asset_path)


def test_skin_layout_keeps_lcd_at_real_1x():
    layout = layout_for_screen(320)
    assert layout.screen_side == 320
    assert layout.host_width < PHOTO_SIZE[0]
    assert layout.host_height < PHOTO_SIZE[1]
    assert 0 < layout.screen_x < layout.host_width
    assert 0 < layout.screen_y < layout.host_height


def test_horizontal_skin_layout_exists():
    layout = layout_for_mode('horizontal', 320)
    assert layout.orientation == 'horizontal'
    assert layout.host_width > layout.host_height
    assert layout.host_width < PHOTO_SIZE_HORIZONTAL[0]


def test_skin_asset_is_packaged_in_repository():
    path = Path(skin_asset_path())
    assert path.is_file()
    assert path.name == 'picocalc-transparent.png'


def test_skin_geometry_contract_matches_reference_photo():
    assert PHOTO_SIZE == (840, 1300)
    assert SCREEN_RECT == (126, 112, 555, 555)


def test_window_offers_skin_modes_in_view_menu():
    source = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text(encoding='utf-8')
    assert "Skin vertical" in source
    assert "Skin horizontal" in source
    assert "Pantalla 2×" in source
    assert "self.display_mode = 'skin-vertical'" in source
    assert 'self.skin_background = SkinKeyboard(self.display_host)' in source
