"""Regresiones de flujo, funciones numericas y teclado de Homografica.

El BAS aportado por el usuario se consulta solo por ruta opcional; no se
empaqueta ni modifica. Las pruebas unitarias son independientes del corpus.
"""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.core.machine import BasicMachine, KeyboardBuffer
from basic_cde.core.expressions import BasicError


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self):
        self.t += 0.02


def test_inline_if_colon_does_not_execute_otherwise():
    source = '''N = 4
IF N = 0 THEN PRINT "MAL": END
PRINT "CONTINUA"
END'''
    assert BasicMachine(source).run() == 'CONTINUA\n'


def test_inline_if_colon_runs_all_actions_on_true_branch():
    source = '''IF 1 THEN X=7 : Y=9
PRINT X;",";Y
END'''
    assert BasicMachine(source).run() == '7,9\n'


def test_nested_function_early_exit_honors_condition():
    source = '''PRINT GCD(15,10)
PRINT GCD(0,4)
END
FUNCTION GCD(X,Y)
 IF X=0 THEN GCD=Y : EXIT FUNCTION
 IF Y=0 THEN GCD=X : EXIT FUNCTION
 DO WHILE Y<>0
   T=X MOD Y
   X=Y : Y=T
 LOOP
 GCD=X
END FUNCTION'''
    assert BasicMachine(source).run() == '5\n4\n'


def test_explicit_byref_scalar_outputs_and_nested_update():
    source = '''A=0 : B=0
SETWINDOW A,B
PRINT A;",";B
END
SUB SETWINDOW(BYREF X, BYREF Y)
 X=4
 ADDONE X
 Y=X+3
END SUB
SUB ADDONE(BYREF Z)
 Z=Z+1
END SUB'''
    assert BasicMachine(source).run() == '5,8\n'


def test_byval_does_not_write_back_to_caller():
    source = '''A=8
CHANGECOPY A
PRINT A
END
SUB CHANGECOPY(BYVAL X)
 X=5
END SUB'''
    assert BasicMachine(source).run() == '8\n'


def test_byref_requires_scalar_variable():
    source = '''F 2+3
END
SUB F(BYREF X)
 X=8
END SUB'''
    with pytest.raises(BasicError, match='BYREF.*requiere variable'):
        BasicMachine(source).run()


def test_min_max_and_math_log10_native_forms():
    source = '''PRINT MIN(3,-4,5)
PRINT MAX(3,-4,5)
PRINT INT(MATH(LOG10 1000))
END'''
    assert BasicMachine(source).run() == '-4\n5\n3\n'


def test_keyboard_clear_discards_stale_menu_keys():
    kb = KeyboardBuffer()
    kb.push('R\r')
    kb.clear()
    assert kb.read() == ''
    kb.push('G')
    assert kb.read() == 'G'


def test_user_homografica_original_waits_and_can_graph():
    source_path = os.environ.get('HOMOGRAFICA_BAS')
    corpus_path = os.environ.get('BAS_CORPUS_ZIP')
    if not source_path or not corpus_path:
        pytest.skip('HOMOGRAFICA_BAS y BAS_CORPUS_ZIP son opcionales')
    if not Path(source_path).is_file() or not Path(corpus_path).is_file():
        pytest.skip('Archivos de corpus no disponibles')

    source = Path(source_path).read_text(encoding='utf-8-sig')
    with ZipFile(corpus_path) as archive:
        library = archive.read('utiles.bas').decode('utf-8-sig')
    clock = FakeClock()
    keys = KeyboardBuffer()
    machine = BasicMachine(source, libraries=[library], clock=clock, keyboard=keys)
    output = ''
    for _ in range(7000):
        result = machine.step()
        output += result.output
        if result.state == 'waiting_input':
            machine.input_value('1,2,3,4')
        if result.state == 'waiting_time':
            clock.advance()
        if '[R]epetir' in output:
            break
    else:
        pytest.fail('No se alcanzo menu de resultado en Homografica')
    for fragment in ('Vertical en x = -4/3', 'Horizontal en y = 1/3',
                     'Absisas en y = 1/2', 'Ordenadas en x = -2'):
        assert fragment in output
    # Sin teclas, se queda en espera, no reinicia el formulario.
    for _ in range(1200):
        result = machine.step()
        assert 'Ingrese a,b,c,d:' not in result.output
        if result.state == 'waiting_time':
            clock.advance()
    keys.push('G')
    graphics_count = 0
    for _ in range(30000):
        result = machine.step()
        graphics_count += bool(result.graphics)
        if result.state == 'waiting_time':
            clock.advance()
        if graphics_count >= 100:
            break
    assert graphics_count >= 100
