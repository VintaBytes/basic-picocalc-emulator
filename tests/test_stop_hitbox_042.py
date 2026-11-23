"""STOP clicable por icono y texto; modo 2× subido 5 píxeles."""
from pathlib import Path
import ast

WINDOW = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py')


def test_stop_label_and_red_square_share_one_clickable_hitbox():
    source = WINDOW.read_text(encoding='utf-8')
    ast.parse(source)
    assert "self.stop_label = QLabel('STOP', self.display_host)" in source
    assert "self.stop_hitbox = QPushButton('', self.display_host)" in source
    assert 'self.stop_hitbox.clicked.connect(self.stop_run)' in source
    assert 'self.stop_hitbox.setGeometry(bx - 3, by - 3,' in source
    assert 'group_width + 6, side + 6)' in source
    assert 'self.stop_hitbox.raise_()' in source
    assert 'self.stop_hitbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)' in source


def test_stop_hitbox_follows_execution_state():
    source = WINDOW.read_text(encoding='utf-8')
    assert source.count('self.stop_hitbox.setEnabled(True)') >= 1
    assert source.count('self.stop_hitbox.setEnabled(False)') >= 1
    assert 'self.stop_button.clicked.connect(self.stop_run)' in source


def test_only_large_mode_moves_stop_up():
    source = WINDOW.read_text(encoding='utf-8')
    assert "if mode == 'large':\n            by = max(2, by - 5)" in source
    assert 'self.stop_label.setGeometry(bx + side + gap, by - 2,' in source
    assert 'self.stop_button.setGeometry(bx, by, side, side)' in source
