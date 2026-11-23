"""Regresiones de DATE$/TIME$ y espera prolongada de teclado."""
from datetime import datetime, timedelta
from basic_cde.core.machine import BasicMachine, ScopedVariables
from basic_cde.core.expressions import BasicError
import pytest


def test_rtc_uses_local_clock_and_updates():
    now = [datetime(2026, 11, 6, 18, 4, 9)]
    vars_ = ScopedVariables(wall_clock=lambda: now[0])
    assert vars_.get('DATE$') == '06-11-2026'
    assert vars_.get('TIME$') == '18:04:09'
    now[0] += timedelta(seconds=2)
    assert vars_.get('TIME$') == '18:04:11'


def test_set_rtc_does_not_modify_host_and_validates():
    now = [datetime(2026, 11, 6, 18, 4, 9)]
    vars_ = ScopedVariables(wall_clock=lambda: now[0])
    vars_['DATE$'] = '15-12-2026'
    vars_['TIME$'] = '09:10:11'
    assert (vars_['DATE$'], vars_['TIME$']) == ('15-12-2026', '09:10:11')
    assert now[0] == datetime(2026, 11, 6, 18, 4, 9)
    now[0] += timedelta(seconds=1)
    assert vars_['TIME$'] == '09:10:12'
    with pytest.raises(BasicError, match='DATE'):
        vars_['DATE$'] = '31-02-2026'
    with pytest.raises(BasicError, match='TIME'):
        vars_['TIME$'] = '29:01:00'


def test_mmbasic_expressions_and_header_format():
    code = '''PRINT DATE$
PRINT TIME$
PRINT LEFT$(DATE$,2)+"/"+MID$(DATE$,4,2)+"/"+RIGHT$(DATE$,2)
END'''
    machine = BasicMachine(code)
    machine.variables.wall_clock = lambda: datetime(2026, 11, 6, 19, 20, 21)
    out = ''
    for _ in range(12):
        result = machine.step()
        out += result.output
        if result.state == 'finished': break
    assert '06-11-2026' in out
    assert '19:20:21' in out
    assert '06/11/26' in out


def test_rtc_assignment_basic_code():
    machine = BasicMachine('DATE$="01-01-2027"\nTIME$="12:30:00"\nPRINT DATE$;" ";TIME$\nEND')
    output = ''
    for _ in range(10):
        result = machine.step()
        output += result.output
        if result.state == 'finished': break
    assert '01-01-2027 12:30:00' in output


def test_long_key_polling_has_no_fixed_instruction_cap():
    machine = BasicMachine('DO\nK$=INKEY$\nLOOP UNTIL K$<>""\nPRINT "OK"\nEND')
    # No existe una excepción por superar el umbral histórico.
    machine.instructions = 500_000
    for _ in range(20):
        assert machine.step().state == 'running'
    machine.keyboard.push('x')
    for _ in range(20):
        result = machine.step()
        if result.output:
            assert 'OK' in result.output
            break
    else:
        pytest.fail('No termino al inyectar la tecla')
