"""Auditoria MMBasic 6.00.03: limites de expresion en comandos graficos."""
import pytest

from basic_cde.core.machine import BasicMachine, _split_graphic_args
from basic_cde.core.expressions import BasicError, evaluate


def run_until_graphics(machine, max_steps=30):
    for _ in range(max_steps):
        result = machine.step()
        if result.graphics and result.graphics[0] == 'text':
            return result.graphics
    raise AssertionError('No se produjo TEXT')


def test_landmine_text_extra_closing_parenthesis():
    program = (
        'TankX=2:TankY=3:TankOrientation=1:TankColor=123\n'
        'TEXT (TankX-1)*16,(TankY-1)*16,CHR$(33+TankOrientation)),,9,2,TankColor,RGB(BEIGE)\n'
    )
    machine = BasicMachine(program)
    command = run_until_graphics(machine)
    assert command[0:4] == ('text', 16, 32, '"')
    assert command[4:7] == (None, 9, 2)
    assert len(machine.warnings) == 1
    assert machine.warnings[0].startswith('Warning: TEXT ')
    assert 'linea fuente 2' in machine.warnings[0]


def test_graphic_commas_inside_parentheses_remain_grouped():
    fields, warning_count = _split_graphic_args('0,(1+2),RGB(2,3,4),"a,b"')
    assert fields == ['0', '(1+2)', 'RGB(2,3,4)', '"a,b"']
    assert warning_count == 0


def test_graphic_extra_closes_before_comma_or_end():
    fields, count = _split_graphic_args('1,CHR$(65)),,RGB(WHITE))')
    assert fields == ['1', 'CHR$(65)', '', 'RGB(WHITE)']
    assert count == 2


def test_unmatched_close_inside_quoted_text_is_not_warning():
    fields, count = _split_graphic_args('1,2,"hola))",,9')
    assert fields == ['1', '2', '"hola))"', '', '9']
    assert count == 0


def test_general_expression_remains_strict():
    with pytest.raises(BasicError, match='Expresion sobrante'):
        evaluate('(1+2))')


def test_invalid_expression_inside_text_still_errors():
    machine = BasicMachine('TEXT 1,2,(3+),,9')
    with pytest.raises(BasicError):
        machine.step()


def test_warning_not_part_of_framebuffer_or_print():
    machine = BasicMachine('TEXT 0,0,"A"),,9\nPRINT "OK"\nEND')
    first = machine.step()
    assert first.graphics[0] == 'text'
    assert 'Warning' not in first.output
    assert len(machine.warnings) == 1
    assert machine.step().output == 'OK\n'
