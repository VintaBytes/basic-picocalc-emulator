"""Regresiones PRINT @ con coordenadas anidadas (PicoCalc Commander)."""
import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_nested_coordinate_from_pcc_dialog():
    src = 'i=2\nPRINT @(132,72+(i+2)*12,2) "S";\nEND'
    m = BasicMachine(src)
    assert m.step().state == 'running'
    result = m.step()
    assert result.graphics == ('print_at', 132, 120, 'S', 2)
    assert m.step().state == 'finished'


def test_nested_both_axes_and_mode():
    m = BasicMachine('i=3\nPRINT @(10*(i+1), 8+(i+2)*12, 1+1) "OK"\nEND')
    m.step()
    assert m.step().graphics == ('print_at', 40, 68, 'OK', 2)


def test_pcc_dialog_other_print_at_forms():
    m = BasicMachine('i=3\nPRINT @(60,80+i*12) "MENSAJE"\nPRINT @(132+36,72+(i+2)*12,2) "N";\nPRINT @(72,72+(i+2)*12,2);\nEND')
    m.step()
    assert m.step().graphics == ('print_at', 60, 116, 'MENSAJE', 0)
    assert m.step().graphics == ('print_at', 168, 132, 'N', 2)
    assert m.step().graphics == ('print_at', 72, 132, '', 2)


def test_missing_closing_parenthesis_is_clear_error():
    with pytest.raises(BasicError, match='PRINT @: falta parentesis'):
        BasicMachine('PRINT @(20,30+(4*2) "x"').step()


def test_legacy_simple_print_at_is_preserved():
    assert BasicMachine('PRINT @(8,8,2) "A";').step().graphics == ('print_at', 8, 8, 'A', 2)


def test_actual_pcc_dialog_sn_branch_until_user_answer():
    """Ejecutar rutina Dialog real de PCC, sin tocar el BAS original."""
    from pathlib import Path
    from unittest.mock import patch
    from basic_cde.app.session import BasicSession
    from basic_cde.core.machine import KeyboardBuffer

    path = Path(__file__).resolve().parents[1] / 'examples' / 'pcc-273-ajustado.bas'
    text = path.read_text(encoding='utf-8')
    dialog = text[text.index('Sub Dialog('):text.index('Sub Progress(')]
    getkey = text[text.index('Sub GetKey'):text.index('FUNCTION PadToNextRow$')]
    src = ('DIM STRING k$ = ""\n'
           'Dialog "Borrar archivo?", "SN", RGB(RED)\n'
           'PRINT "DESPUES"\nEND\n' + dialog + '\n' + getkey)
    kb = KeyboardBuffer()
    kb.push('n')
    session = BasicSession(src, keyboard=kb)
    outputs = []
    with patch.object(session, '_audio_action', return_value=None):
        for _ in range(200):
            r = session.step()
            if r.output:
                outputs.append(r.output)
            if r.state == 'finished':
                break
        else:
            pytest.fail('Dialog PCC no finaliza tras respuesta N')
    assert 'DESPUES\n' in outputs
