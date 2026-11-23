"""Regresion comprobada en WebMite RP2350A 6.00003 real, 2026-11-09."""
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_webmite_ignore_1_multiple_explicit_errors_real_hardware():
    program = '''OPTION EXPLICIT
ON ERROR IGNORE 1
X$ = "primero"
PRINT "PASO 1"
Y$ = "segundo"
PRINT "PASO 2"
ON ERROR ABORT
PRINT "FIN"'''
    assert BasicMachine(program).run().splitlines() == ['PASO 1','PASO 2','FIN']


def test_ignore_1_still_active_after_successful_statements():
    program = '''OPTION EXPLICIT
ON ERROR IGNORE 1
PRINT "OK"
UNDECLARED$="X"
PRINT "SIGUE"
UNDECLARED2$="X"
PRINT "FIN"'''
    assert BasicMachine(program).run().splitlines() == ['OK', 'SIGUE', 'FIN']


def test_ignore_1_abort_restores_strict_option_explicit():
    with pytest.raises(BasicError,match='Variable no declarada'):
        BasicMachine('OPTION EXPLICIT\nON ERROR IGNORE 1\nX$="A"\nON ERROR ABORT\nY$="B"').run()


def test_skip_1_is_not_ignore_1():
    with pytest.raises(BasicError,match='Variable no declarada'):
        BasicMachine('OPTION EXPLICIT\nON ERROR SKIP 1\nX$="A"\nY$="B"').run()


def test_explicit_still_rejects_variables_without_ignore():
    with pytest.raises(BasicError,match='Variable no declarada'):
        BasicMachine('OPTION EXPLICIT\nDEST$="B:/"').run()
