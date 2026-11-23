"""Contratos de presentación: ningún cambio de semántica BASIC ni GUI ficticia."""
from pathlib import Path


WINDOW = Path(__file__).parents[1] / 'src/basic_cde/gui/window.py'
PROJECT = Path(__file__).parents[1] / 'pyproject.toml'


def test_brand_and_no_technical_footer():
    source = WINDOW.read_text(encoding='utf-8')
    assert "self.heading = QLabel('BASIC PicoCalc Linux')" not in source
    assert 'LINUX  /  MMBasic compatible  /  PicoCalc' not in source
    assert 'PANTALLA  /  320' not in source
    assert 'self.program_box =' not in source
    assert 'self.mount_label =' not in source
    assert 'self.library_summary =' not in source


def test_manage_actions_are_available_from_menus():
    source = WINDOW.read_text(encoding='utf-8')
    for label in ('Archivo', 'Unidades', 'Bibliotecas', 'Ver', 'Ayuda'):
        assert f".addMenu('{label}')" in source
    for method in ('mount_flash', 'mount_disk', 'add_library', 'show_transcript',
                   'show_info', 'show_about'):
        assert f'self.{method}' in source
    assert 'self.drives.roots[unit]' in source
    assert "self.program_dirty" in source


def test_keyboard_menu_interactions_not_redirected_to_ready():
    source = WINDOW.read_text(encoding='utf-8')
    assert 'QApplication.activePopupWidget() is None' in source
    assert 'QApplication.activeModalWidget() is None' in source
    assert 'self._routing_ready_key = True' in source
    assert 'self.command.keyPressEvent(event)' in source


def test_new_command_keeps_old_alias_and_preserves_settings():
    pyproject = PROJECT.read_text(encoding='utf-8')
    settings = (WINDOW.parents[1] / 'app/settings.py').read_text(encoding='utf-8')
    assert 'basic-picocalc = "basic_cde.__main__:main"' in pyproject
    assert 'basic-cde = "basic_cde.__main__:main"' in pyproject
    assert "'basic-cde-linux' / 'settings.json'" in settings
