"""Contratos de interfaz verificables aun sin PySide6 instalado.

Las pruebas interactivas de Qt se hacen en un Ubuntu con el extra [gui].
"""
from pathlib import Path


def _window_source():
    return (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()


def test_screen_scale_uses_nearest_neighbour():
    source = _window_source()
    assert "Skin vertical" in source
    assert "Skin horizontal" in source
    assert "Pantalla 2×" in source
    assert 'self.screen.setFixedSize(layout.screen_side,layout.screen_side)' in source
    assert 'Qt.TransformationMode.FastTransformation' in source
    assert 'self.framebuffer.snapshot()' in source


def test_input_remains_inside_lcd_and_keyboard_gate_is_preserved():
    source = _window_source()
    assert 'self.command = QLineEdit(self.screen)' in source
    assert 'self.input_key_gate.after_input()' in source
    assert 'self.worker.send_input(text)' in source


def test_all_drive_and_library_controls_are_preserved():
    source = _window_source()
    for method in ('mount_flash', 'mount_disk', 'add_library', 'show_transcript',
                   'start_run', 'stop_run', 'open_file'):
        assert f'self.{method}' in source
