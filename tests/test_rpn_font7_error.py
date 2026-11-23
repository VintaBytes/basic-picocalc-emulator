"""Regresiones de las observaciones en RPN2G; sin Qt ni BAS modificados."""
import os
from pathlib import Path
from zipfile import ZipFile
import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay
from basic_cde.devices.rom_fonts import bundled_fonts


def test_font7_uses_authentic_picomite_bitmap_not_provisional():
    font = bundled_fonts()[7]
    assert (font.width, font.height, font.first, font.count) == (6, 8, 32, 96)
    d = BitmapDisplay()
    d.graphics(('font', 7, 1))
    d.glyph(0, 0, 'A')
    for y in range(font.height):
        for x in range(font.width):
            expected = 255 if font.pixel(ord('A'), x, y) else 0
            assert d.framebuffer.get_pixel(x, y)[:3] == (0, expected, 0)


def test_rpn_on_error_skip_without_count_and_abort():
    src = '''ON ERROR SKIP
A=1/0
PRINT MM.ERRNO
ON ERROR ABORT
PRINT 42
END'''
    assert BasicMachine(src).run().splitlines() == ['1', '42']


def test_on_error_abort_resets_pending_skip():
    with pytest.raises(BasicError):
        BasicMachine('ON ERROR SKIP\nON ERROR ABORT\nA=1/0').run()


def test_original_rpn_on_error_skip_is_supported():
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Necesita BAS_CORPUS_ZIP')
    with ZipFile(archive) as z:
        original = z.read('mate/rpn2g.bas').decode('utf-8-sig')
    assert 'ON ERROR SKIP' in original
    session = BasicSession(original)
    for _ in range(1500):
        result = session.step()
        assert result.state != 'error'
    assert session.display.current_font == 7
