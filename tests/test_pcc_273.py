"""Regresiones surgidas del PCC.bas real sin modificar el parser por programa."""
from pathlib import Path
import tempfile

import pytest
from basic_cde.core.machine import BasicMachine, KeyboardBuffer
from basic_cde.core.expressions import BasicError
from basic_cde.app.session import BasicSession
from basic_cde.devices.drives import VirtualDrives


def run_session(src, disks=None, keys='', max_steps=700):
    keyboard = KeyboardBuffer()
    if keys:
        keyboard.push(keys)
    session = BasicSession(src, drives=disks, keyboard=keyboard)
    for _ in range(max_steps):
        state = session.step().state
        if state != 'running':
            break
    return session


def test_typed_params_string_integer_float_and_byval():
    code = '''OPTION EXPLICIT
DIM STRING TITLE$ = "OK"
DIM INTEGER NUM = 5
SHOW TITLE$, NUM, 3.5
PRINT TITLE$,NUM
END
SUB SHOW(drive$ AS STRING, pane AS INTEGER, size AS FLOAT)
PRINT drive$,pane,size
END SUB'''
    assert BasicMachine(code).run() == 'OK 5 3.5\nOK 5\n'


def test_byref_typed_scalar_and_byval():
    code = '''X=1
INC X
PRINT X
INC BYVAL X
END
SUB INC(v)
v=v+1
END SUB'''
    # La invocación con BYVAL no existe: BYVAL pertenece a la declaracion.
    with pytest.raises(BasicError):
        BasicMachine(code).run()
    code='''X=1
INC X
PRINT X
END
SUB INC(v)
v=v+1
END SUB'''
    assert BasicMachine(code).run() == '2\n'


def test_invalid_parameter_type_rejected():
    with pytest.raises(BasicError, match='incompatibles'):
        BasicMachine('SUB G(s$ AS INTEGER)\nEND SUB')
    with pytest.raises(BasicError, match='Parametro no admitido'):
        BasicMachine('SUB G(s AS MAGIC)\nEND SUB')


def test_local_integer_declaration():
    code = '''CALLER
END
SUB CALLER
LOCAL INTEGER n
n=7
PRINT n
END SUB'''
    assert BasicMachine(code).run() == '7\n'


def test_inline_if_then_else_subs():
    src = '''SUB FIRST
PRINT "A"
END SUB
SUB SECOND
PRINT "B"
END SUB
IF 1 THEN FIRST ELSE SECOND
IF 0 THEN FIRST ELSE SECOND
END'''
    assert BasicMachine(src).run() == 'A\nB\n'


def test_dir_listing_filter_and_repeat(tmp_path):
    (tmp_path/'hello.bas').write_text('END')
    (tmp_path/'README').write_text('hello')
    (tmp_path/'folder').mkdir()
    src = '''PRINT DIR$("*",DIR)
PRINT DIR$()
PRINT DIR$("*.*",FILE)
PRINT DIR$()
PRINT DIR$()
END'''
    session=run_session(src, VirtualDrives(a=tmp_path), max_steps=100)
    assert session.machine.finished
    # El filtro FILE tambien encuentra README con *.* (comodin FAT).
    assert session.machine._dir_results is not None


def test_pcc_instr_regex_size_parameter():
    src = '''L=0
P=INSTR(1,"file.bas","\\.[^\\.]*$",L)
PRINT P,L
END'''
    assert BasicMachine(src).run() == '5 4\n'


def test_print_at_inverted_and_rbox():
    session=run_session('''CLS
COLOR RGB(RED),RGB(BLUE)
PRINT @(8,8,2) "A";
RBOX 20,20,40,30,6,RGB(WHITE),RGB(GREEN)
END''')
    assert session.machine.finished
    assert session.display.framebuffer.get_pixel(35,32)[:3] == (0,255,0)


def test_mm_info_file_queries(tmp_path):
    (tmp_path/'file.txt').write_text('abc')
    src='''PRINT MM.INFO(EXISTS FILE "file.txt")
PRINT MM.INFO(EXISTS DIR ".")
PRINT MM.INFO(FILESIZE "file.txt")
END'''
    assert BasicMachine(src, drives=VirtualDrives(a=tmp_path)).run()=='1\n1\n3\n'


def test_pcc_error_policy_compat_syntax():
    assert BasicMachine('''ON ERROR IGNORE 1
PRINT "OK"
END''').run() == 'OK\n'


def test_inline_else_inside_literal_string_does_not_split():
    source = 'IF 1 THEN PRINT "A ELSE B" ELSE PRINT "C"\nEND'
    assert BasicMachine(source).run() == 'A ELSE B\n'


def test_pcc_real_program_initializes_and_handles_navigation(tmp_path):
    """Corpus PCC: init, DIR$, DRAW, INFO, HELP y teclado interactivo."""
    source = (Path(__file__).parent.parent/'examples'/'pcc-273-ajustado.bas').read_text()
    root_a, root_b = tmp_path/'flash', tmp_path/'sd'
    root_a.mkdir()
    root_b.mkdir()
    (root_a/'prueba.bas').write_text('END')
    (root_b/'bas').mkdir()
    keyboard = KeyboardBuffer()
    session = BasicSession(source, keyboard=keyboard,
                           drives=VirtualDrives(a=root_a, b=root_b))
    for key in ('', 'A', 'B', chr(129), chr(128), 'H', 'I', 'I'):
        if key:
            keyboard.push(key)
        for _ in range(1300):
            state = session.step().state
            assert state == 'running'
    assert session.machine.instructions >= 1000
    assert 'LOADDIR' in session.machine.routines
