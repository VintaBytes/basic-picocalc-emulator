"""Regresiones del skin horizontal compuesto, sin dependencia de PySide6."""
from pathlib import Path

from basic_cde.gui.skin import (
    PHOTO_SIZE_HORIZONTAL,
    LED_CENTER_VERTICAL,
    horizontal_skin_asset_path,
    led_center_for_mode,
    screen_rect_for_mode,
    layout_for_mode,
)
from basic_cde.gui.skin_keys import KEY_ZONES_VERTICAL, KEY_ZONES_HORIZONTAL, key_at


def test_horizontal_png_is_bundled_and_has_correct_size():
    path = Path(horizontal_skin_asset_path())
    assert path.is_file()
    assert path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
    assert PHOTO_SIZE_HORIZONTAL == (1479, 648)


def test_horizontal_lcd_is_on_left_and_at_exactly_1x():
    layout = layout_for_mode('horizontal', 320)
    assert layout.screen_side == 320
    assert layout.host_width > layout.host_height
    assert layout.screen_x + 320 < layout.host_width // 2 + 30
    assert screen_rect_for_mode('horizontal') == (81, 72, 555, 555)


def test_horizontal_keys_are_to_right_and_clickable():
    assert len(KEY_ZONES_HORIZONTAL) == len(KEY_ZONES_VERTICAL)
    for zone in KEY_ZONES_HORIZONTAL:
        cx, cy = zone.x + zone.width / 2, zone.y + zone.height / 2
        assert key_at(cx, cy, 'horizontal') == zone.name
        assert zone.x > 760


def test_led_coordinates_match_original_indicator():
    assert LED_CENTER_VERTICAL == (705, 171)
    assert led_center_for_mode('horizontal') == (660, 131)
