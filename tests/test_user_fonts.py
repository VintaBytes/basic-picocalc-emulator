"""Pruebas headless: mapa DEFINEFONT original y tipografia personalizada."""
import os
from pathlib import Path
import zipfile

import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay


def font_example():
    # 1 glyph 8x8, 'A' = 65, 8 bytes of bitmap, with the first pixel lit.
    header = bytes((8, 8, 65, 1))
    pixels = bytes((128, 0, 0, 0, 0, 0, 0, 0))
    words = [data[::-1].hex().upper() for data in (header, pixels[:4], pixels[4:])]
    return '\n'.join(['DEFINEFONT #10', *words, 'END DEFINEFONT',
                      'FONT 10,2', 'TEXT 2,3,"A"', 'END'])


def test_font_declaration_is_not_executed_as_basic_instructions():
    m = BasicMachine(font_example())
    graphics = []
    for _ in range(6):
        result = m.step()
        if result.graphics:
            graphics.append(result.graphics)
        if result.state == 'finished':
            break
    assert [cmd[0] for cmd in graphics] == ['definefont', 'font', 'text']
    assert graphics[0][1:5] == (10, 8, 8, 65)
    d = BitmapDisplay()
    for cmd in graphics:
        d.graphics(cmd)
    assert d.framebuffer.get_pixel(2, 3) == (0, 255, 0, 255)
    assert d.framebuffer.get_pixel(3, 3) == (0, 255, 0, 255)
    assert d.framebuffer.get_pixel(4, 3) == (0, 0, 0, 255)


def test_font_changing_works_for_print_as_well_as_text():
    m = BasicMachine(font_example().replace('TEXT 2,3,"A"', 'PRINT "A"'))
    d = BitmapDisplay()
    for _ in range(6):
        result = m.step()
        if result.graphics:
            d.graphics(result.graphics)
        if result.output:
            d.console(result.output)
        if result.state == 'finished':
            break
    assert d.framebuffer.get_pixel(0, 0) == (0, 255, 0, 255)
    assert d.framebuffer.get_pixel(1, 0) == (0, 255, 0, 255)
    assert d.framebuffer.get_pixel(2, 0) == (0, 0, 0, 255)


def test_font_declaration_accepts_truncated_data_like_firmware():
    cmd = BasicMachine('DEFINEFONT #10\n01410808\nEND DEFINEFONT').step().graphics
    assert cmd[:5] == ('definefont', 10, 8, 8, 65)
    assert cmd[-1] == b''


def test_font_undefined_fails_explicitly():
    d = BitmapDisplay()
    with pytest.raises(BasicError, match='no definida'):
        d.graphics(('font', 10, 1))


def test_sokoban_original_font_when_corpus_is_available():
    archive = os.getenv('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('BAS_CORPUS_ZIP no disponible')
    with zipfile.ZipFile(archive) as z:
        raw = z.read('juegosg/sokoban.bas').decode('utf-8-sig')
    machine = BasicMachine(raw)
    font_cmd = machine.step().graphics
    assert font_cmd[:5] == ('definefont', 10, 8, 8, 32)
    assert len(font_cmd[-1]) == 8 * 224
    display = BitmapDisplay()
    display.graphics(font_cmd)
    display.graphics(('font', 10, 2))
    display.graphics(('text', 10, 10, 'SOKOBAN'))
    assert display.framebuffer.snapshot() != BitmapDisplay().framebuffer.snapshot()


def test_font_one_trailing_glyph_accepted_but_not_exposed():
    # Cabecera anuncia un glifo 8x8 y los datos incluyen dos glifos.
    program = "DEFINEFONT #9\n01410808\n01020304 05060708\n11121314 15161718\nEND DEFINEFONT\n"
    machine = BasicMachine(program)
    command = machine.step().graphics
    assert command[:5] == ('definefont', 9, 8, 8, 65)
    assert len(command[-1]) == 8
    assert command[-1] == bytes.fromhex('0403020108070605')


def test_font_multiple_extra_glyphs_are_ignored():
    program = "DEFINEFONT #9\n01410808\n" + "01020304 05060708\n" * 3 + "END DEFINEFONT\n"
    cmd = BasicMachine(program).step().graphics
    assert len(cmd[-1]) == 8


def test_demo_bas_three_fonts_parse_without_modifying_original():
    corpus = Path(__file__).resolve().parents[1] / 'examples' / 'demo-graficos-original.bas'
    assert corpus.is_file()
    m = BasicMachine(corpus.read_text(encoding='ascii'))
    assert len(m._font_definitions) == 3
    assert [(f[1], f[2], f[3], f[4], len(f[5])) for f in m._font_definitions] == [
        (9, 8, 8, 32, 760),
        (10, 16, 16, 32, 256),
        (11, 8, 12, 48, 96),
    ]
