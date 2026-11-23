"""Observaciones en PicoCalc fisica: TAB y PUSH reservados (MMBasic 6.00.03)."""
import pytest

from basic_cde.core.expressions import evaluate
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


@pytest.mark.parametrize('statement', [
    'DIM TAB(21,16)',
    'dim tab(21,16)',
    'DIM tab AS INTEGER',
    'tab=0',
    'LET tab=0',
    'tab(0,0)=1',
])
def test_tab_name_is_not_variable(statement):
    with pytest.raises(BasicError, match='Variable name'):
        BasicMachine(statement).run()


@pytest.mark.parametrize('statement', [
    'PUSH = 0',
    'push=1',
    'LET Push=0',
    'DIM PUSH',
    'DIM PUSH(2)',
])
def test_push_is_reserved_pio_command(statement):
    with pytest.raises(BasicError, match='missing Program statement'):
        BasicMachine(statement).run()


def test_tab_function_remains_available():
    assert evaluate('TAB(5)') == '    '
    assert BasicMachine('PRINT TAB(5);"OK"').run() == '    OK\n'


def test_non_reserved_names_remain_legal():
    assert BasicMachine('DIM pushCount=0\nDIM tablet(2)\nPRINT pushCount').run() == '0\n'
