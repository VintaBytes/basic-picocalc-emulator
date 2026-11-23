"""Regresiones sobre menu logaritmico y editor en pantalla."""
import os
from pathlib import Path
from zipfile import ZipFile
import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.devices.display import BitmapDisplay
from basic_cde.gui.inline_input import input_anchor, input_preview


def test_assignment_to_array_ignores_parens_and_equals_inside_string():
    source = '''DIM textos$(3)
textos$(1) = "ANALISIS DE y = LOG_a(m*x+b)"
textos$(2) = "LOG_a(m*x+b) = k"
textos$(3) = "LOG_a(m*x+b) = LOG_a(n*x+d)"
PRINT textos$(2)
END'''
    machine = BasicMachine(source)
    assert machine.run() == 'LOG_a(m*x+b) = k\n'
    assert machine.variables['TEXTOS$'].read([3]) == 'LOG_a(m*x+b) = LOG_a(n*x+d)'


def test_subscripts_with_nested_expression():
    source = '''DIM A$(5)
I=2
A$(INT(I+1))="a=b) ok"
PRINT A$(3)
END'''
    assert BasicMachine(source).run() == 'a=b) ok\n'


def test_inline_preview_does_not_change_live_framebuffer():
    display = BitmapDisplay()
    display.console('Ingresar a: ')
    anchor = input_anchor(display)
    before = display.framebuffer.snapshot()
    typed = input_preview(anchor, '123')
    replaced = input_preview(anchor, '7')
    assert display.framebuffer.snapshot() == before
    assert typed != before and replaced != typed and replaced != before
    assert input_preview(anchor, '7') == replaced


def test_inline_preview_keeps_font_and_colors():
    display = BitmapDisplay()
    display.graphics(('font', 7, 2))
    display.graphics(('color', 0x00FF00, 0))
    display.console('Numero: ')
    new = input_preview(input_anchor(display), '123')
    assert len(new) == 320 * 320 * 4
    assert new != display.framebuffer.snapshot()


def test_logarithm_original_menu(tmp_path):
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Configurar BAS_CORPUS_ZIP')
    with ZipFile(archive) as zipped:
        menu = zipped.read('mate/m_log.bas').decode('utf-8-sig')
        library = zipped.read('utiles.bas').decode('utf-8-sig')
    machine = BasicMachine(menu, libraries=[library])
    for _ in range(500):
        result = machine.step()
        assert result.state not in ('finished', 'chain')
    assert machine.variables['TEXTOS$'].read([2]) == 'LOG_a(m*x+b) = k'
