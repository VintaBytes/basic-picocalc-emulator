"""STR$ MMBasic 6.00.03: Functions.c/fun_str(), MENU.BAS de suite."""
import pytest

from basic_cde.core.expressions import BasicError, evaluate
from basic_cde.core.machine import BasicMachine


@pytest.mark.parametrize(('expression', 'expected'), [
    ('STR$(1)', '1'),
    ('STR$(1,0,0)', '1'),
    ('STR$(6,0,0)', '6'),
    ('STR$(12,0,2)', '12.00'),
    ('STR$(7,4,0)', '   7'),
    ('STR$(7,4,0,"0")', '0007'),
    ('STR$(-7,4,0,"0")', '-007'),
    ('STR$(7,-4,0,"0")', '+007'),
    ('STR$(7,0,0)', '7'),
    ('STR$(1.25,0,2)', '1.25'),
    ('STR$(1.255,0,2)', '1.26'),
])
def test_str_format(expression, expected):
    assert evaluate(expression) == expected


@pytest.mark.parametrize('expression', [
    'STR$()', 'STR$(1,2,3,"0",5)', 'STR$("1")',
    'STR$(1,129)', 'STR$(1,0,21)', 'STR$(1,0,0,"")'
])
def test_str_invalid_arguments(expression):
    with pytest.raises(BasicError):
        evaluate(expression)


def test_suite_menu_drawrow_str_3_parameters():
    # La linea 131 original de suite/MENU.BAS.
    machine = BasicMachine(
        'row=1:yy=53:accent=1:fill=2\n'
        'TEXT 12,yy+8,STR$(row,0,0),"LT",1,1,accent,fill\n'
        'END'
    )
    # La primera linea contiene cuatro asignaciones separadas por ':'.
    # Cada una consume un step(); TEXT se ejecuta en el quinto paso.
    graphics = []
    for _ in range(12):
        result = machine.step()
        if result.graphics:
            graphics.append(result.graphics)
        if result.state == 'finished':
            break
    assert graphics == [('text', 12, 61, '1', 'LT', 1, 1, 1, 2)]


def test_str_dispatch_in_expression_parser():
    from basic_cde.core.expressions import ExpressionParser
    assert ExpressionParser('STR$(4,0,0)', {}).parse() == '4'
