"""Prueba end-to-end del mismo BAS que se transfiere a la PicoCalc real."""
from pathlib import Path

from basic_cde.core.machine import BasicMachine


PROGRAM = Path(__file__).parents[1] / 'examples/regresion-compatibilidad-250.bas'
ORIGINAL = Path(__file__).parents[1] / 'examples/regresion-compatibilidad-249.bas'


def test_regression_program_is_ascii_for_picocalc_charset():
    source = PROGRAM.read_text(encoding='ascii')
    assert 'SUB TESTN(' in source
    assert 'SUB TESTS(' in source
    assert 'LONGSTRING' in source
    assert 'JSON$(' in source
    assert 'ON ERROR SKIP 2' in source


def test_regression_program_runs_without_hardware_and_checks_expected_values():
    output = BasicMachine(PROGRAM.read_text(encoding='ascii')).run()
    assert 'TOTAL=81\n' in output
    assert 'OK=81\n' in output
    assert 'FAIL=0\n' in output
    assert 'RESULTADO: PASS\n' in output
    assert 'FAIL ' not in output


def test_regression_program_reports_actual_vs_expected_when_a_check_fails():
    source = PROGRAM.read_text(encoding='ascii')
    source = source.replace('TESTN "EXP0",EXP(0),1,0.00001',
                            'TESTN "EXP0",EXP(0),42,0.00001')
    output = BasicMachine(source).run()
    assert 'FAIL EXP0\n' in output
    assert ' ESP=42 OBT=1\n' in output
    assert 'TOTAL=81\n' in output
    assert 'OK=80\n' in output
    assert 'FAIL=1\n' in output
    assert 'RESULTADO: FAIL\n' in output


def test_original_249_is_retained_and_rejected_due_to_real_hardware_rule():
    import pytest
    from basic_cde.core.expressions import BasicError
    with pytest.raises(BasicError, match='Array Dimensions'):
        BasicMachine(ORIGINAL.read_text(encoding='ascii')).run()
