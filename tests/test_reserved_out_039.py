"""OUT como comando PIO de MMBasic 6.00.03, no como identificador.

Caso real reportado: MAT_HOMOGRAFICA.BAS usa la matriz out$(24).
No se corrige ni se modifica el archivo BAS original.
"""
import pytest

from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine


@pytest.mark.parametrize("statement", [
    'DIM fieldText$(4),out$(24)',
    'DIM out$(24)',
    'DIM OUT AS INTEGER',
    'OUT = 0',
    'out$="hola"',
    'LET out$="hola"',
    'out$(1)="hola"',
])
def test_out_reserved_name_rejected(statement):
    with pytest.raises(BasicError, match="missing Program statement"):
        BasicMachine(statement + "\nEND").run()


def test_homografica_original_declaration_fails_at_line_7():
    source = ("' comentario\n" * 6) + 'DIM fieldText$(4),out$(24)\nEND'
    with pytest.raises(BasicError, match=r"missing Program statement.*linea fuente 7"):
        BasicMachine(source).run()


def test_valid_distinct_identifiers_remain_supported():
    source = ('DIM outputLines$(24)\n'
              'outCount=1:outputLines$(outCount)="OK"\n'
              'PRINT outputLines$(outCount)\nEND')
    assert BasicMachine(source).run() == "OK\n"
