"""Regresiones de la fuente de 6x8 dibujada específicamente para CDE Linux."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.machine import KeyboardBuffer
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay
from basic_cde.devices.font6x8 import GLYPHS_6X8


def test_font7_thin_regular_glyphs_and_cell_metrics():
    assert len(GLYPHS_6X8) == 95
    for rows in GLYPHS_6X8:
        assert len(rows) == 8
        assert rows[-1] == 0  # fila inferior libre dentro de la celda
        assert all(0 <= row <= 0xF8 for row in rows)
        assert all(row & 0x04 == 0 for row in rows)  # ultima columna vacia
    assert GLYPHS_6X8[ord('0') - 32] != GLYPHS_6X8[ord('8') - 32]
    assert GLYPHS_6X8[ord('I') - 32] != GLYPHS_6X8[ord('l') - 32]


def test_font7_scale_two_advances_twelve_pixels_and_print_is_legible():
    display = BitmapDisplay()
    display.graphics(('font', 7, 2))
    display.console('AB')
    assert display.col == 2
    assert display._font_info(7) == (6, 8)
    # Separacion: 12 pixels por celda; la ultima fila del glifo queda libre.
    assert all(display.framebuffer.get_pixel(x, 14)[:3] == (0, 0, 0)
               for x in range(24))
    assert any(display.framebuffer.get_pixel(x, y)[:3] != (0, 0, 0)
               for y in range(0, 14) for x in range(0, 12))
    assert any(display.framebuffer.get_pixel(x, y)[:3] != (0, 0, 0)
               for y in range(0, 14) for x in range(12, 24))


def test_font7_rpn_real_renders_menu_without_error():
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Requiere BAS_CORPUS_ZIP')
    with ZipFile(archive) as z:
        source = z.read('mate/rpn2g.bas').decode('utf-8-sig')
    session = BasicSession(source, keyboard=KeyboardBuffer())
    for _ in range(2500):
        result = session.step()
        assert result.state != 'error'
    assert session.display.current_font == 7
    assert session.display.font_scale == 2
    fb = session.display.framebuffer
    assert any(fb.get_pixel(x, y)[:3] != (0, 0, 0)
               for x in range(16, 280) for y in range(4, 15))
