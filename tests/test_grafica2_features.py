"""Regresiones derivadas del programa Grafica2, sin tocar fuentes originales."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.app.session import BasicSession
from basic_cde.devices.drives import VirtualDrives


def test_radix_literals_and_formatting():
    src = '''PRINT &H47524631
PRINT &B1010
PRINT &O17
PRINT FORMAT$(12.3456,"%.3g")
END'''
    assert BasicMachine(src).run().splitlines() == [
        '1196574257', '10', '15', '12.3']


def test_on_error_skip_and_eval_expression_string():
    src = '''X=2
ON ERROR SKIP 1
Y=EVAL("3 / 0")
PRINT MM.ERRNO
ON ERROR SKIP 1
Y=EVAL("X*SIN(X)")
PRINT MM.ERRNO
PRINT Y
END'''
    machine = BasicMachine(src)
    output = machine.run().splitlines()
    assert output[:2] == ['1', '0']
    assert float(output[2]) == pytest.approx(2 * __import__('math').sin(2))


def test_on_error_skip_does_not_hide_second_error():
    with pytest.raises(BasicError):
        BasicMachine('ON ERROR SKIP 1\nPRINT EVAL("1/0")\nPRINT EVAL("1/0")').run()


def test_local_string_array_is_typed_string():
    source = """OPTION BASE 0
VERIFY
PRINT RESULT
END
SUB VERIFY
  LOCAL N$(2)
  N$(0)="OK"
  RESULT=LEN(N$(0))
END SUB"""
    assert BasicMachine(source).run() == "2\n"


def test_local_explicit_string_array_without_suffix():
    source = """OPTION BASE 1
VERIFY
PRINT RESULT
END
SUB VERIFY
  LOCAL STRING NOTE(2)
  NOTE(1)="texto"
  RESULT=LEN(NOTE(1))
END SUB"""
    assert BasicMachine(source).run() == "5\n"


def test_local_integer_array_keeps_integer_values():
    source = """OPTION BASE 1
VERIFY
PRINT RESULT
END
SUB VERIFY
  LOCAL N%(2)
  N%(1)=27
  RESULT=N%(1)
END SUB"""
    assert BasicMachine(source).run() == "27\n"


def test_local_arrays_and_optional_box_argument():
    src = '''OPTION BASE 0
A
PRINT RESULT
END
SUB A
  LOCAL N$(2)
  N$(0)="OK"
  RESULT=LEN(N$(0))
  BOX 5,6,20,10, ,RGB(255,0,0),RGB(0,0,0)
END SUB'''
    assert BasicMachine(src).run() == '2\n'


def test_file_operations_and_on_error_missing_file(tmp_path):
    drives = VirtualDrives(a=tmp_path)
    src = '''ON ERROR SKIP 1
OPEN "missing.cfg" FOR INPUT AS #1
PRINT MM.ERRNO
OPEN "grafica.cfg" FOR OUTPUT AS #1
PRINT #1, "func$=x*sin(x)"
CLOSE #1
OPEN "grafica.cfg" FOR INPUT AS #1
LINE INPUT #1, L$
PRINT L$
PRINT EOF(#1)
CLOSE #1
END'''
    assert BasicMachine(src, drives=drives).run().splitlines() == [
        '1', 'func$=x*sin(x)', '1']
    assert (tmp_path/'grafica.cfg').read_text() == 'func$=x*sin(x)\n'


def test_continue_do_skips_rest_of_iteration():
    source = '''N=0
S=0
DO WHILE N<5
 N=N+1
 IF N MOD 2=0 THEN CONTINUE DO
 S=S+N
LOOP
PRINT S
END'''
    assert BasicMachine(source).run() == '9\n'


@pytest.mark.parametrize('with_config', [False, True])
def test_grafica2_original_draws_both_curves_and_exits(tmp_path, with_config):
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Definir BAS_CORPUS_ZIP')
    with ZipFile(archive) as z:
        original = z.read('mate/grafica2.bas').decode('utf-8-sig')
        cfg = z.read('mate/grafica.cfg')
        library = z.read('utiles.bas').decode('utf-8-sig')
    sd = tmp_path/'sd'
    folder = sd/'bas'/'mate'
    folder.mkdir(parents=True)
    if with_config:
        (folder/'grafica.cfg').write_bytes(cfg)
    drives = VirtualDrives(b=sd)
    drives.drive('B:')
    drives.chdir('bas/mate')
    now = [0.]
    def clock():
        now[0] += 0.025
        return now[0]
    session = BasicSession(original, drives=drives, clock=clock, libraries=[library])
    session.machine.keyboard.push(chr(27))  # ESC en configuracion
    operations = {}
    pressed = False
    for step in range(20_000):
        result = session.step()
        if result.graphics:
            op = result.graphics[0]
            operations[op] = operations.get(op, 0) + 1
        if not pressed and operations.get('line',0) > 500:
            # Tomamos la captura ANTES de que el programa borre la pantalla al salir.
            pixels = session.display.framebuffer.pixels
            colors = {bytes(pixels[k:k+3]) for k in range(0,len(pixels),4)}
            assert bytes.fromhex('00ffff') in colors  # curva cian
            assert bytes.fromhex('ffd700') in colors  # curva dorada
            session.machine.keyboard.push('q')
            pressed = True
        if result.state == 'finished':
            break
    else:
        pytest.fail('Grafica2 no completo su recorrido con ESC + Q')
    assert pressed
    assert operations['line'] >= 500
    assert (folder/'grafica.cfg').is_file()
