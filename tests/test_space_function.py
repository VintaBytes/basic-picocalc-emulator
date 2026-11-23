"""SPACE$ es usado por MenuDibujarLinea de la biblioteca real utiles.bas."""
import pytest
from basic_cde.core.expressions import evaluate, BasicError
from basic_cde.core.machine import BasicMachine


def test_space_sizes():
    assert evaluate('SPACE$(0)') == ''
    assert evaluate('SPACE$(4)') == '    '
    assert evaluate('"[" + SPACE$(3) + "]"') == '[   ]'


def test_space_invalid_arguments():
    for expr in ('SPACE$(-1)', 'SPACE$(1.5)', 'SPACE$(256)', 'SPACE$("A")'):
        with pytest.raises(BasicError, match=r'SPACE\$'):
            evaluate(expr)


def test_space_does_not_trim_text_redraw():
    source = 'N=5\nTEXT 10,20,SPACE$(N)\nPRINT "OK"\nEND'
    machine = BasicMachine(source)
    operations = []
    for _ in range(10):
        result = machine.step()
        if result.graphics:
            operations.append(result.graphics)
        if result.state == 'finished':
            break
    assert any(op[0] == 'text' and '     ' in str(op) for op in operations)


def test_instr_mmbasic_1_based_and_optional_start():
    assert evaluate('INSTR("RUN|B:/bas/menu.bas", "|")') == 4
    assert evaluate('INSTR(4, "A-B-C", "-")') == 4
    assert evaluate('INSTR("abc", "z")') == 0
    assert evaluate('INSTR("abc", "b")') == 2
    with pytest.raises(BasicError, match='INSTR'):
        evaluate('INSTR(0, "ABC", "A")')
