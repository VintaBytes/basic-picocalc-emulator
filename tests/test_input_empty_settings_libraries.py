"""Regresiones: INPUT vacio y bibliotecas persistentes."""
import json
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.app.settings import MountSettings
from basic_cde.core.expressions import BasicError


def test_numeric_input_blank_is_zero():
    program = 'INPUT "GASTO (0..100 KG/S): ", G\nPRINT G + 5\nEND'
    assert BasicMachine(program).run(input_provider=lambda prompt: '') == '5\n'


def test_numeric_input_spaces_is_zero():
    assert BasicMachine('INPUT X\nPRINT X').run(input_provider=lambda _: '   ') == '0\n'


def test_string_input_blank_is_empty():
    assert BasicMachine('INPUT S$\nPRINT "["; S$; "]"').run(input_provider=lambda _: '') == '[]\n'


def test_invalid_nonempty_numeric_input_still_errors():
    with pytest.raises(BasicError):
        BasicMachine('INPUT X').run(input_provider=lambda _: 'xyz??')


def test_library_persistence_preserves_mounts(tmp_path):
    store = MountSettings(tmp_path / 'settings.json')
    store.save({'B': '/home/user/sd'})
    store.save_libraries(['/home/user/sd/bas/utiles.bas', '/home/user/sd/bas/utiles.bas'])
    assert store.load() == {'B': '/home/user/sd'}
    assert store.load_libraries() == ['/home/user/sd/bas/utiles.bas']
    store.save({'A': '/tmp/flash', 'B': '/home/user/sd'})
    assert store.load_libraries() == ['/home/user/sd/bas/utiles.bas']
    assert json.loads(store.path.read_text())['version'] == 1


def test_old_settings_are_backward_compatible(tmp_path):
    store = MountSettings(tmp_path / 'settings.json')
    store.path.write_text('{"version":1,"mounts":{"A":"/flash"}}')
    assert store.load_libraries() == []
    store.save_libraries(['/sd/utiles.bas'])
    assert store.load() == {'A': '/flash'}


def test_corrupt_library_list_is_ignored(tmp_path):
    store = MountSettings(tmp_path / 'settings.json')
    store.path.write_text('{"version":1,"mounts":{},"libraries":"no-list"}')
    assert store.load_libraries() == []
