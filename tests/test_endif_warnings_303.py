"""Compatibilidad con END IF tolerado por MMBasic 6.00.03.

En Commands.c cmd_null es el handler de END IF / ENDIF. Nuestro parser
mantiene diagnósticos de estructura sin volverlos fatales.
"""
import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.app.session import BasicSession


@pytest.mark.parametrize('terminator', ['END IF', 'ENDIF', 'end if'])
def test_unmatched_endif_is_noop_with_warning(terminator):
    m = BasicMachine('PRINT "ANTES"\n' + terminator + '\nPRINT "DESPUES"\nEND')
    assert m.warnings == [
        'Warning: END IF sin IF de bloque (linea fuente 2)'
    ]
    assert m.step().output == 'ANTES\n'
    assert m.step().state == 'running'
    assert m.step().output == 'DESPUES\n'
    assert m.step().state == 'finished'


def test_well_formed_multiline_if_has_no_warning():
    m = BasicMachine('IF 1 THEN\nPRINT "OK"\nEND IF\nEND')
    assert m.warnings == []
    assert m.step().state == 'running'
    assert m.step().output == 'OK\n'


def test_inline_if_followed_by_stray_endif_is_tolerated():
    m = BasicMachine('IF 1 THEN PRINT "A" ELSE PRINT "B"\nEND IF\nEND')
    assert len(m.warnings) == 1
    for _ in range(10):
        if m.step().state == 'finished':
            break


def test_incomplete_if_block_remains_fatal():
    with pytest.raises(BasicError, match='Bloque IF sin cerrar'):
        BasicMachine('IF 1 THEN\nPRINT "OK"\nEND')


def test_nested_block_and_stray_endif():
    m = BasicMachine('IF 1 THEN\nIF 1 THEN\nPRINT "OK"\nEND IF\nEND IF\nEND IF\nEND')
    assert len(m.warnings) == 1
    assert 'linea fuente 6' in m.warnings[0]


def test_diagnostics_not_written_to_basic_display():
    session = BasicSession('END IF\nPRINT "LISTO"\nEND')
    assert len(session.machine.warnings) == 1
    first = session.step()
    assert first.output == ''
    second = session.step()
    assert second.output == 'LISTO\n'
    assert 'Warning' not in second.output
