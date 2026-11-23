"""Regresiones MM.INFO basadas en demo.bas de la PicoCalc real."""
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def run(source):
    m = BasicMachine(source)
    outputs = []
    for _ in range(100):
        result = m.step()
        if result.output:
            outputs.append(result.output)
        if result.state == 'finished':
            break
    return m, ''.join(outputs)


def test_builtin_font_dimensions_and_version():
    m, output = run('PRINT MM.INFO(FONTWIDTH),MM.INFO(FONTHEIGHT)\nFONT 7,2\nPRINT MM.INFO(FONT),MM.INFO(FONTWIDTH),MM.INFO(FONTHEIGHT)\nPRINT MM.INFO(HRES),MM.INFO(VRES)\nPRINT MM.INFO(VERSION)\nEND')
    assert output.startswith('8 12\n')
    assert m.variables['MM.ERRNO'] == 0
    assert m.active_font == 7
    assert '320' in output
    assert '6.0003' in output
    assert m.value('MM.INFO(FONTWIDTH)') == 12
    assert m.value('MM.INFO(FONTHEIGHT)') == 16


def test_definefont_resolved_before_first_statement():
    # Original custom-font header 5F200808 is 8x8 with 95 glyphs.
    glyphs = ['00000000'] * (95*2)
    source = '\n'.join(['DEFINEFONT #9','5F200808',*glyphs,'END DEFINEFONT',
                        'FONT 9,4','W=MM.INFO(FONTWIDTH)', 'H=MM.INFO(FONTHEIGHT)', 'END'])
    m,_ = run(source)
    assert m.variables['W'] == 32
    assert m.variables['H'] == 32


def test_mm_info_unknown_does_not_coerce_argument_to_zero():
    m = BasicMachine('END')
    with pytest.raises(BasicError, match='opcion no disponible'):
        m.value('MM.INFO(NOT_IMPLEMENTED)')
    with pytest.raises(BasicError, match='argumento invalido'):
        m.value('MM.INFO(2)')


def test_mm_info_color_matches_basic_state():
    m, _ = run('COLOR RGB(5,6,7),RGB(8,9,10)\nA=MM.INFO(FCOLOUR)\nB=MM.INFO(BCOLOUR)\nEND')
    assert m.variables['A'] == 0x050607
    assert m.variables['B'] == 0x08090A
