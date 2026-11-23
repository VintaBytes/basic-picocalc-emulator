"""Contrato del diseño fotográfico sin barra superior (reemplaza toolbar 0.2.44)."""
from pathlib import Path

WINDOW = Path(__file__).parents[1] / 'src/basic_cde/gui/window.py'


def test_all_skin_modes_have_no_floating_toolbar():
    src = WINDOW.read_text(encoding='utf-8')
    assert 'self.toolbar' not in src
    assert 'self.position_toolbar()' not in src
    assert 'vertical.setContentsMargins(0,0,0,0)' in src
    assert 'self.setFixedSize(self._skin_layout.host_width,' in src
    assert "self._enable_skin('horizontal')" in src


def test_menu_actions_survive_toolbar_removal():
    src = WINDOW.read_text(encoding='utf-8')
    for label in ("'Abrir programa .BAS...'", "'Editar BASIC'", "'Ejecutar'", "'Detener'"):
        assert label in src
    assert 'self.stop_button.clicked.connect(self.stop_run)' in src
    assert "self.stop_label = QLabel('STOP', self.display_host)" in src
