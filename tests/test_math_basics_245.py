"""Regresiones matematicas para BASIC PicoCalc Linux 0.2.45-dev.

El banco de referencia fisica esta en examples/diagnostico-matematico.bas.
"""
import math
import pytest

from basic_cde.core.expressions import BasicError, evaluate
from basic_cde.core.machine import BasicMachine


def test_inverse_trig_radians_and_argument_order():
    assert evaluate('ASIN(1)') == pytest.approx(math.pi / 2)
    assert evaluate('ACOS(0)') == pytest.approx(math.pi / 2)
    assert evaluate('ATAN2(1,0)') == pytest.approx(math.pi / 2)
    assert evaluate('ATAN2(0,-1)') == pytest.approx(math.pi)
    assert evaluate('ATAN2(-1,0)') == pytest.approx(-math.pi / 2)


def test_inverse_trig_respects_option_angle_degrees():
    program = '''OPTION ANGLE DEGREES
PRINT ASIN(1)
PRINT ACOS(0)
PRINT ATAN2(1,0)
PRINT ATAN2(0,-1)
OPTION ANGLE RADIANS
PRINT ATAN2(1,0)
END'''
    values = [float(line) for line in BasicMachine(program).run().splitlines()]
    assert values == pytest.approx([90, 90, 90, 180, math.pi / 2])


def test_exp_and_inverse_log_and_boundaries():
    assert evaluate('EXP(0)') == 1
    assert evaluate('EXP(1)') == pytest.approx(math.e)
    assert evaluate('LOG(EXP(2))') == pytest.approx(2)
    for expression in ('ASIN(1.001)', 'ACOS(-2)', 'EXP(10000)'):
        with pytest.raises(BasicError):
            evaluate(expression)


def test_cint_fix_rounding_and_negative_fractions():
    assert evaluate('FIX(-2.9)') == -2
    assert evaluate('FIX(2.9)') == 2
    assert evaluate('CINT(2.4)') == 2
    assert evaluate('CINT(2.6)') == 3
    assert evaluate('CINT(-2.4)') == -2
    assert evaluate('CINT(-2.6)') == -3
    assert evaluate('CINT(2.5)') == 3
    assert evaluate('CINT(-2.5)') == -3


def test_hex_bin_oct_and_optional_width():
    assert evaluate('HEX$(255)') == 'FF'
    assert evaluate('HEX$(255,4)') == '00FF'
    assert evaluate('BIN$(10)') == '1010'
    assert evaluate('BIN$(10,8)') == '00001010'
    assert evaluate('OCT$(9)') == '11'
    assert evaluate('OCT$(9,4)') == '0011'
    assert evaluate('HEX$(0)') == '0'
    assert evaluate('HEX$(-1)') == 'FFFFFFFFFFFFFFFF'


def test_reject_invalid_arity_or_types():
    for expression in ('ATAN2(1)', 'ASIN()', 'CINT("abc")', 'HEX$(1,-1)',
                       'BIN$(2,65)', 'OCT$(1,2.5)', 'HEX$(1,2,3)', 'EXP("x")'):
        with pytest.raises(BasicError):
            evaluate(expression)


def test_program_uses_new_functions_in_expressions():
    program = '''OPTION ANGLE DEGREES
PRINT CINT(EXP(0)+2.4)
PRINT HEX$(255,4)
PRINT ASIN(1)
PRINT ATAN2(1,1)
END'''
    lines = BasicMachine(program).run().splitlines()
    assert lines[0] == '3'
    assert lines[1] == '00FF'
    assert [float(lines[2]), float(lines[3])] == pytest.approx([90, 45])
