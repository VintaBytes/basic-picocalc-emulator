"""Regresiones de la semantica documentada de OPTION F y las macros READY."""
import json
import pytest
from basic_cde.app.function_keys import parse_option_fn, key_text, split_key_input
from basic_cde.app.settings import MountSettings
from basic_cde.app.direct import DirectConsole
from basic_cde.core.expressions import BasicError


def test_option_expression_and_carriage_return():
    key, text = parse_option_fn('OPTION F1 "RUN " + CHR$(34) + "B:/bas/menu.bas" + CHR$(34) + CHR$(13)')
    assert key == 1
    assert text == 'RUN "B:/bas/menu.bas"\r'
    assert split_key_input(text) == (['RUN "B:/bas/menu.bas"'], '')


def test_f5_option_inserts_text_until_carriage_return():
    assert parse_option_fn('option f5 "PRINT 5"') == (5, 'PRINT 5')
    assert split_key_input('PRINT 5') == ([], 'PRINT 5')
    assert split_key_input('RUN\r\n') == (['RUN'], '')
    assert key_text(2, {}) == 'RUN\r'
    assert key_text(3, {}) == 'LIST\r'
    assert key_text(4, {}) == 'EDIT\r'
    assert key_text(1, {}) == ''
    assert key_text(5, {5: 'PRINT 5\r'}) == 'PRINT 5\r'


def test_option_rejects_keys_reserved_by_firmware_and_invalid_expr():
    for cmd in ('OPTION F2 "RUN"', 'OPTION F10 "X"', 'OPTION F8 123', 'OPTION F5 "unclosed'):
        with pytest.raises(BasicError):
            parse_option_fn(cmd)


def test_options_direct_only_and_do_not_alter_program():
    direct = DirectConsole('10 PRINT "UNO"\n')
    r = direct.execute('OPTION F5 "RUN"+CHR$(13)')
    assert r.action == 'option_function_key'
    assert r.argument == '5\x00RUN\r'
    assert direct.source == '10 PRINT "UNO"\n'
    assert direct.execute('OPTION LIST').action == 'option_list'
    assert direct.execute('NEW').action == 'new'


def test_settings_persist_macro_and_other_fields(tmp_path):
    cfg = MountSettings(tmp_path / 'settings.json')
    cfg.save({'A': tmp_path, 'B': tmp_path})
    cfg.save_libraries([tmp_path / 'utiles.bas'])
    cfg.save_last_program(tmp_path / 'menu.bas')
    cfg.save_function_keys({1: 'RUN "B:/bas/menu.bas"\r', 5: 'RUN "B:/bas/calculadora.bas"\r'})
    assert MountSettings(cfg.path).load_function_keys()[1].endswith('\r')
    assert MountSettings(cfg.path).load()['A'] == str(tmp_path)
    cfg.save({'B': tmp_path})
    assert cfg.load_function_keys()[5].startswith('RUN')
    assert cfg.load_libraries() == [str(tmp_path / 'utiles.bas')]
    assert cfg.load_last_program().endswith('menu.bas')
    assert json.loads(cfg.path.read_text())['version'] == 1


def test_gui_keeps_function_keys_out_of_running_programs():
    from pathlib import Path
    src = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()
    assert 'and self.direct_ready and self.isActiveWindow()' in src
    assert 'self._apply_ready_macro(macro, function_number=number)' in src
    assert 'self.command.keyPressEvent(event)' in src
    assert 'self.resize(760, 790)' in src
