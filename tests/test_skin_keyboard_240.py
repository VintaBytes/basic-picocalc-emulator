"""Geometría y seguridad del teclado gráfico sin dependencia de PySide6."""
from pathlib import Path
import struct
from basic_cde.gui.skin import (LED_CENTER_VERTICAL, PHOTO_SIZE, PHOTO_SIZE_HORIZONTAL,
                                SCREEN_RECT, layout_for_mode, layout_for_screen, skin_asset_path)
from basic_cde.gui.skin_keys import (KEY_ZONES, KEY_ZONES_HORIZONTAL, key_at,
                                     visual_key_for_host)


def test_carcass_white_border_is_transparent_but_photo_remains_intact():
    data = Path(skin_asset_path()).read_bytes()
    assert data[:8] == bytes((137, 80, 78, 71, 13, 10, 26, 10))
    assert struct.unpack('>II', data[16:24]) == PHOTO_SIZE
    assert data[25] == 6  # PNG RGBA; el canal alpha elimina el marco blanco


def test_screen_is_18_source_pixels_higher():
    assert SCREEN_RECT == (126, 112, 555, 555)
    assert layout_for_screen(320).screen_y < 75


def test_photo_contains_all_keys_and_hit_test():
    names = [zone.name for zone in KEY_ZONES]
    for name in ('Enter', 'F1', 'F5', 'Esc', 'Space', 'ShiftLeft',
                 'ShiftRight', 'Ctrl', 'Alt', 'Up', 'Down', 'Left', 'Right',
                 'A', 'Z', '1', '0'):
        assert names.count(name) == 1
        zone = next(zone for zone in KEY_ZONES if zone.name == name)
        assert key_at(zone.x + zone.width / 2, zone.y + zone.height / 2) == name
    assert key_at(0, 0) is None


def test_horizontal_keyboard_rotation_and_led_contract():
    assert PHOTO_SIZE_HORIZONTAL == (1479, 648)
    assert len(KEY_ZONES_HORIZONTAL) == len(KEY_ZONES)
    led_x, led_y = LED_CENTER_VERTICAL
    assert led_x > 680 and led_y < 250
    layout = layout_for_mode('horizontal', 320)
    assert layout.host_width > layout.host_height


def test_pc_physical_f_keys_share_picture_buttons():
    assert visual_key_for_host(1000, '', qt_f1=1000, qt_a=65, qt_0=48, qt_1=49) == 'F1'
    assert visual_key_for_host(1005, '', qt_f1=1000, qt_a=65, qt_0=48, qt_1=49) == 'F1'
    assert visual_key_for_host(65, 'a', qt_f1=1000, qt_a=65, qt_0=48, qt_1=49) == 'A'


def test_press_animation_and_clicks_do_not_reinject_qt_events():
    window = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()
    widget = (Path(__file__).parents[1] / 'src/basic_cde/gui/skin_widget.py').read_text()
    assert 'self.skin_background.flash_key(name)' in window
    assert 'self.command.keyPressEvent(key_event)' in window
    assert 'self.worker.send_key(value)' in window
    assert 'self.skin_background.keyClicked.connect(self.on_skin_key_clicked)' in window
    assert 'QApplication.sendEvent' not in widget
    assert 'QTimer.singleShot(duration_ms, release)' in widget
    assert 'self._draw_led(painter)' in widget
