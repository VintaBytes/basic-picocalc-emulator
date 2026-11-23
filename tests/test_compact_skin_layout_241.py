"""Contratos visuales del modo skin compacto (sin dependencia de Qt)."""
from pathlib import Path

WINDOW = Path(__file__).parents[1] / 'src/basic_cde/gui/window.py'


def test_compact_design_has_no_heading_or_panel_borders():
    text = WINDOW.read_text(encoding='utf-8')
    assert "self.heading = QLabel(" not in text
    assert 'QFrame#tool-panel, QFrame#lcd-frame { background: transparent; border: none; }' in text
    assert 'vertical.setContentsMargins(0,0,0,0)' in text
    assert 'lcd_frame_layout.setContentsMargins(0, 0, 0, 0)' in text


def test_toolbar_removed_and_stop_integrated_in_skin():
    text = WINDOW.read_text(encoding='utf-8')
    assert "QPushButton('Abrir .BAS')" not in text
    assert "QPushButton('Editar BASIC')" not in text
    assert "QPushButton('▶  Ejecutar')" not in text
    assert "QPushButton('', self.display_host)" in text
    assert "self.stop_label = QLabel('STOP', self.display_host)" in text
    assert 'self.stop_button.raise_()' in text
    assert "menu_file.addAction('Editar BASIC'" in text

def test_skin_sizes_itself_without_affecting_plain_mode():
    text = WINDOW.read_text(encoding='utf-8')
    assert 'def resize_to_skin(self):' in text
    assert 'self.setFixedSize(self._skin_layout.host_width,' in text
    assert 'self.statusBar().hide()' in text
    assert 'self.setMaximumSize(16777215,16777215)' in text
    assert "self._enable_skin('large' if scale==2 else 'compact')" in text


def test_input_and_skin_keyboard_still_connected():
    text = WINDOW.read_text(encoding='utf-8')
    assert 'self.skin_background.keyClicked.connect(self.on_skin_key_clicked)' in text
    assert 'self.command = QLineEdit(self.screen)' in text
    assert 'self.command.keyPressEvent(event)' in text
