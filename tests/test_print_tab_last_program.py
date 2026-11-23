"""Regresiones: PRINT TAB adyacente y preferencia de ultimo BAS."""
import json
from basic_cde.core.machine import BasicMachine
from basic_cde.app.settings import MountSettings


def test_print_tab_immediately_followed_by_string():
    code = 'TAB1=5\nPRINT TAB(TAB1)" vzzw"\nEND'
    assert BasicMachine(code).run() == '     vzzw\n'


def test_print_tab_with_separator_and_in_string():
    assert BasicMachine('PRINT TAB(3);"OK"\nEND').run() == '  OK\n'
    assert BasicMachine('PRINT "TAB(7)"\nEND').run() == 'TAB(7)\n'


def test_print_tab_multiple_items_and_comma():
    assert BasicMachine('PRINT TAB(3)"ABC";"!"\nEND').run() == '  ABC!\n'
    assert BasicMachine('PRINT TAB(3),"ABC"\nEND').run() == '   ABC\n'


def test_last_program_preserves_libraries_and_mounts(tmp_path):
    cfg = MountSettings(tmp_path / 'config.json')
    cfg.save({'A': str(tmp_path / 'flash'), 'B': str(tmp_path / 'sd')})
    cfg.save_libraries([tmp_path / 'utiles.bas'])
    cfg.save_last_program(tmp_path / 'sokoban.bas')
    assert cfg.load_last_program() == str(tmp_path / 'sokoban.bas')
    assert cfg.load()['B'] == str(tmp_path / 'sd')
    assert cfg.load_libraries() == [str(tmp_path / 'utiles.bas')]
    cfg.save({'B': tmp_path / 'new-sd'})
    assert cfg.load_last_program().endswith('sokoban.bas')
    cfg.save_libraries([tmp_path / 'other.bas'])
    assert cfg.load_last_program().endswith('sokoban.bas')
    assert json.loads(cfg.path.read_text())['version'] == 1


def test_last_program_corrupt_value_is_ignored(tmp_path):
    cfg = MountSettings(tmp_path / 'config.json')
    assert cfg.load_last_program() is None
    cfg.path.write_text('{"version":1,"last_program":12}')
    assert cfg.load_last_program() is None
