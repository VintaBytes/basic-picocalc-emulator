"""FUNCTION interrumpibles sin reiniciar bucles ni duplicar efectos."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.core.machine import BasicMachine, KeyboardBuffer
from basic_cde.app.session import BasicSession
from basic_cde.devices.drives import VirtualDrives


class FakeClock:
    def __init__(self):
        self.time = 0.0

    def __call__(self):
        return self.time

    def advance(self, seconds):
        self.time += seconds


def drain(machine, clock, *, n=300, key_at=None):
    outputs = []
    states = []
    for i in range(n):
        if key_at is not None and i == key_at[0]:
            machine.keyboard.push(key_at[1])
        result = machine.step()
        states.append(result.state)
        outputs.append(result.output)
        if result.state == 'waiting_time':
            clock.advance(0.02)
        if result.state == 'finished':
            return ''.join(outputs), states
    pytest.fail(f'No termino tras {n} pasos; pc={machine.pc}')


def test_inkey_pause_function_preserves_local_state_and_return():
    clock = FakeClock()
    program = '''N = 5
PRINT "INICIO"
X$ = TECLA$()
PRINT X$
PRINT N
END
FUNCTION TECLA$()
  LOCAL C$
  DO
    C$ = INKEY$
    IF C$ <> "" THEN EXIT DO
    PAUSE 10
  LOOP
  TECLA$ = C$
END FUNCTION'''
    machine = BasicMachine(program, clock=clock)
    output, states = drain(machine, clock, key_at=(40, 'Z'))
    assert output == 'INICIO\nZ\n5\n'
    assert states.count('waiting_time') >= 2
    assert machine.call_stack == []
    assert machine.variables.frames == []


def test_nested_function_resumes_and_returns_correct_result():
    clock = FakeClock()
    source = '''PRINT 100 + OUTER(3)
END
FUNCTION OUTER(X)
  LOCAL K
  K = INNER(X)
  OUTER = K + 2
END FUNCTION
FUNCTION INNER(X)
  PAUSE 10
  INNER = X * 4
END FUNCTION'''
    m = BasicMachine(source, clock=clock)
    output, states = drain(m, clock)
    assert output == '114\n'
    assert 'waiting_time' in states
    assert not m.call_stack


def test_restored_data_read_into_array_by_numeric_level_label():
    source = '''OPTION BASE 1
DIM A(2,2)
N=2
RESTORE N
FOR Y=1 TO 2
 FOR X=1 TO 2
  READ A(X,Y)
 NEXT X
NEXT Y
PRINT A(2,2)
RESTORE 1
READ Z
PRINT Z
END
1 DATA 9,8,7,6
2 DATA 2,3,4,5'''
    clock = FakeClock()
    output, _ = drain(BasicMachine(source, clock=clock), clock)
    assert output == '5\n9\n'


def test_restore_without_argument_and_strings():
    m = BasicMachine('''READ A$, B
PRINT A$,B
RESTORE
READ C$
PRINT C$
END
DATA "hola, mundo",10''')
    output = m.run()
    assert output == 'hola, mundo 10\nhola, mundo\n'


def test_original_sokoban_reaches_gameplay_without_gui(tmp_path):
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).exists():
        pytest.skip('Corpus original no disponible')
    with ZipFile(archive) as z:
        source = z.read('juegosg/sokoban.bas').decode('utf-8-sig')
        library = z.read('utiles.bas').decode('utf-8-sig')
    sd = tmp_path / 'sd'
    (sd / 'juegosg').mkdir(parents=True)
    drives = VirtualDrives(b=sd)
    drives.chdir('B:/juegosg')
    clock = FakeClock()
    keyboard = KeyboardBuffer()
    session = BasicSession(source, drives=drives, clock=clock,
                           keyboard=keyboard, libraries=[library])
    # Portada -> menu -> jugar nivel. La prueba solo inyecta teclas
    # desde el dispositivo, sin editar el programa ni la biblioteca.
    for i in range(40000):
        if i == 5000:
            keyboard.push('J')
        if i == 15000:
            keyboard.push(chr(128))
        if i == 17000:
            keyboard.push(chr(13))
        result = session.step()
        if result.state == 'waiting_time':
            clock.advance(0.011)
        if (sd / 'juegosg' / 'nivel2.bmp').exists():
            break
    else:
        pytest.fail('Sokoban original no alcanzo el escenario jugable')
    assert (sd / 'juegosg' / 'portada.bmp').read_bytes()[:2] == b'BM'
    assert (sd / 'juegosg' / 'nivel2.bmp').read_bytes()[:2] == b'BM'
    assert not session.machine.finished


def test_input_inside_function_can_suspend_and_resume():
    source = '''PRINT PEDIR() + 1
END
FUNCTION PEDIR()
  LOCAL N
  INPUT N
  PEDIR = N
END FUNCTION'''
    m = BasicMachine(source)
    assert m.step().state == 'waiting_input'
    m.input_value('41')
    out = []
    for _ in range(20):
        r = m.step()
        out.append(r.output)
        if r.state == 'finished':
            break
    assert ''.join(out) == '42\n'
    assert not m.call_stack


def test_chain_inside_function_bubbles_to_session(tmp_path):
    sd = tmp_path / 'sd'
    sd.mkdir()
    (sd / 'next.bas').write_text('PRINT "CONTINUO"\nEND', encoding='utf8')
    drives = VirtualDrives(b=sd)
    drives.drive('B:')
    source = '''PRINT F()
END
FUNCTION F()
 RUN "next.bas"
 F=123
END FUNCTION'''
    session = BasicSession(source, drives=drives)
    outputs = []
    for _ in range(40):
        r = session.step()
        outputs.append(r.output)
        if r.state == 'finished':
            break
    assert ''.join(outputs) == 'CONTINUO\n'
    assert session.chain_count == 1


def test_function_polling_inkey_yields_without_pause():
    """LeerTeclaCodigo%() real no usa PAUSE: nunca debe congelar la GUI."""
    source = """PRINT GETCODE%()
END
FUNCTION GETCODE%()
 LOCAL K$
 DO
  K$ = INKEY$
 LOOP UNTIL K$ <> ""
 GETCODE% = ASC(K$)
END FUNCTION"""
    m = BasicMachine(source)
    for _ in range(6):
        assert m.step().state == 'running'
        assert not m.finished
    m.keyboard.push('K')
    result = []
    for _ in range(20):
        r = m.step()
        result.append(r.output)
        if r.state == 'finished':
            break
    assert ''.join(result) == '75\n'
    assert not m.call_stack
