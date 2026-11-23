"""Funciones compartidas por las demos graficas de la SD PicoCalc.

No se modifica ni se redistribuye ninguno de los programas originales.
"""
import math
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.app.session import BasicSession
from basic_cde.devices.display import BitmapDisplay


def test_angle_degrees_and_radians_are_distinct():
    program = '''OPTION ANGLE DEGREES
PRINT SIN(90)
PRINT COS(180)
PRINT ATN(1)
OPTION ANGLE RADIANS
PRINT SIN(PI/2)
PRINT RAD(180)
PRINT DEG(PI)
END'''
    numbers = [float(x) for x in BasicMachine(program).run().splitlines()]
    assert numbers == pytest.approx([1, -1, 45, 1, math.pi, 180])


def test_decimal_literals_and_picomite_screen_constants():
    text = BasicMachine('PRINT .01, -.15, 1., PI, MM.HRES, MM.VRES').run().split()
    assert [float(x) for x in text] == pytest.approx([.01, -.15, 1, math.pi, 320, 320])


def test_dim_typed_initializers_and_option_default_none():
    src = '''OPTION DEFAULT NONE
DIM FLOAT X=1.5, Y=-.2
DIM Z AS INTEGER=5
DIM V%(2)=(3,7,11)
PRINT X+Y+Z+V%(1)
END'''
    assert float(BasicMachine(src).run().strip()) == pytest.approx(13.3)
    with pytest.raises(BasicError, match='tipo no especificado'):
        BasicMachine('OPTION DEFAULT NONE\nDIM X\nEND').run()


def test_option_explicit_rejects_undeclared_assignment_and_allows_const():
    assert BasicMachine('OPTION EXPLICIT\nCONST W=320\nDIM X AS INTEGER\nX=W\nPRINT X').run() == '320\n'
    with pytest.raises(BasicError, match='Variable no declarada: X'):
        BasicMachine('OPTION EXPLICIT\nX=1').run()


def test_polygon_draws_fill_and_outline_from_arrays():
    source = '''DIM X%(2)=(8,24,8)
DIM Y%(2)=(8,8,24)
POLYGON 3,X%(),Y%(),RGB(255,0,0),RGB(0,255,0)
END'''
    session = BasicSession(source)
    for _ in range(12):
        if session.step().state == 'finished':
            break
    assert session.display.framebuffer.get_pixel(12, 12)[:3] == (0, 255, 0)
    assert session.display.framebuffer.get_pixel(8, 8)[:3] == (255, 0, 0)
    assert session.display.framebuffer.get_pixel(26, 26)[:3] == (0, 0, 0)


def test_print_at_graphics_position():
    session = BasicSession('PRINT @(30,20) "A"\nEND')
    assert session.step().graphics == ('print_at', 30, 20, 'A', 0)
    assert any(session.display.framebuffer.get_pixel(x,y)[:3] != (0,0,0)
               for x in range(30,38) for y in range(20,32))


def test_original_graphic_programs_reach_drawing_or_keyboard():
    path = os.environ.get('BAS_CORPUS_ZIP')
    if not path or not Path(path).exists():
        pytest.skip('BAS_CORPUS_ZIP no configurado')
    targets = {'graficos/arbol23.bas': 1,
               'graficos/bifdiag.bas': 1,
               'graficos/mand.bas': 1,
               'graficos/lorenz.bas': 1,
               'graficos/experimental.bas': 1,
               'graficos/dragonred.bas': 1}
    with ZipFile(path) as archive:
        library = archive.read('utiles.bas').decode('latin1')
        for name, minimum_graphics in targets.items():
            session = BasicSession(archive.read(name).decode('latin1'), libraries=[library])
            drawn = 0
            for _ in range(1600):
                result = session.step()
                drawn += bool(result.graphics)
                if result.state in ('finished','waiting_input','waiting_time'):
                    break
            assert drawn >= minimum_graphics, name
