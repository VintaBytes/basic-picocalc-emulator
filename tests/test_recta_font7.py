"""Regresiones originadas en programas de la SD de PicoCalc."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.app.session import BasicSession
from basic_cde.devices.display import BitmapDisplay
from basic_cde.devices.drives import VirtualDrives


def test_else_if_synonym_with_nested_blocks():
    src = '''B=-2
IF B > 0 THEN
 PRINT "MAS"
ELSE IF B < 0 THEN
 PRINT "MENOS"
ELSE
 PRINT "CERO"
END IF
IF B=0 THEN
 PRINT "NO"
ELSE IF B=-2 THEN
 IF 1 THEN
  PRINT "OK"
 END IF
END IF'''
    assert BasicMachine(src).run() == 'MENOS\nOK\n'


@pytest.mark.parametrize('b,expected', [(5, 'MAS'), (-5, 'MENOS'), (0, 'CERO')])
def test_else_if_all_three_branches(b, expected):
    src = f'''B={b}
IF B > 0 THEN
 PRINT "MAS"
ELSE IF B < 0 THEN
 PRINT "MENOS"
ELSE
 PRINT "CERO"
END IF'''
    assert BasicMachine(src).run() == expected+'\n'


@pytest.mark.parametrize('font,dimensions', [(1,(8,12)), (2,(12,20)), (3,(16,24)),
                                              (4,(10,16)), (5,(24,32)), (6,(32,50)),
                                              (7,(6,8)), (8,(4,6))])
def test_standard_fonts_have_picomite_lcd_metrics(font, dimensions):
    d = BitmapDisplay()
    d.graphics(('font', font, 1))
    assert d._font_info(font) == dimensions
    # FONT 6 es numerica (0-9 y ':'), no incluye el caracter A.
    d.console('0' if font == 6 else 'A')
    assert any(d.framebuffer.get_pixel(x,y)[:3] != (0,0,0)
               for x in range(dimensions[0]) for y in range(dimensions[1]))


def test_font7_scale_two_and_transparent_text():
    d = BitmapDisplay()
    d.graphics(('font', 7, 2))
    assert d.font_scale == 2
    assert d._font_info(7) == (6, 8)
    d.graphics(('text', 10, 12, 'RPN', 'LT', 7, 2, 0x00FF00, -1))
    assert any(d.framebuffer.get_pixel(x,y)[:3] == (0,255,0)
               for x in range(10,46) for y in range(12,28))
    assert d.framebuffer.get_pixel(9, 9) == (0,0,0,255)


def test_original_recta_mb_with_else_if_and_user_library(tmp_path):
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Necesita BAS_CORPUS_ZIP')
    with ZipFile(archive) as z:
        src = z.read('mate/recta_mb.bas').decode('utf-8-sig')
        lib = z.read('utiles.bas').decode('utf-8-sig')
    disk = tmp_path/'sd'
    (disk/'bas'/'mate').mkdir(parents=True)
    drives = VirtualDrives(b=disk)
    drives.drive('B:')
    drives.chdir('bas/mate')
    session = BasicSession(src, drives=drives, libraries=(lib,))
    # INPUT m=3, b=-4 debe recorrer la rama ELSE IF.
    supplied = iter(('3', '-4'))
    saw_equation = False
    for _ in range(6000):
        step = session.step()
        if step.state == 'waiting_input':
            session.input_value(next(supplied))
        if 'y =' in step.output and '-4' in step.output:
            saw_equation = True
        if saw_equation:
            break
    assert saw_equation, 'No se alcanzó la rama ELSE IF del programa real'


def test_original_rpn2g_accepts_font7(tmp_path):
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Necesita BAS_CORPUS_ZIP')
    with ZipFile(archive) as z:
        source = z.read('mate/rpn2g.bas').decode('utf-8-sig')
    session = BasicSession(source)
    font_seen = False
    for _ in range(100):
        result = session.step()
        if result.graphics and result.graphics[0] == 'font':
            font_seen = True
            assert session.display._font_info(7) == (6, 8)
            assert session.display.font_scale == 2
            break
    assert font_seen


def test_const_multiple_names_and_line_omitted_thickness():
    src = '''CONST T_REAL=1, T_CPLX=2, T_VEC=3
LINE 0,200,15,200, ,RGB(255,0,0)
PRINT T_REAL+T_CPLX+T_VEC
END'''
    session = BasicSession(src)
    output = ''
    for _ in range(10):
        result = session.step()
        output += result.output
        if result.state == 'finished':
            break
    assert output == '6\n'
    assert session.display.framebuffer.get_pixel(7,200) == (255,0,0,255)


def test_original_rpn2g_draws_initial_interface_without_crash():
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Necesita BAS_CORPUS_ZIP')
    with ZipFile(archive) as z:
        source = z.read('mate/rpn2g.bas').decode('utf-8-sig')
    session = BasicSession(source)
    ops = {}
    for _ in range(900):
        result = session.step()
        if result.graphics:
            name = result.graphics[0]
            ops[name] = ops.get(name, 0) + 1
    assert ops.get('font', 0) >= 2
    assert ops.get('text', 0) >= 5
    assert ops.get('line', 0) >= 2
    assert session.display.font_scale == 2
    assert session.display.current_font == 7
