"""Regresion DEFINEFONT 6.00.03 contrastada con FileIO.c y Draw.c.

Referencia historica: PicoMiteAllVersions commit 63a5f21a0f471e.
"""
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay

def run_font(source):
    m = BasicMachine(source)
    cmd = m.step().graphics
    d = BitmapDisplay()
    d.graphics(cmd)
    return cmd, d

def test_redefine_font8_and_read_from_custom_table():
    cmd, d = run_font("DEFINEFONT #8\n01410808\n00000080 00000000\nEND DEFINEFONT")
    assert cmd[1:5] == (8, 8, 8, 65)
    assert d._font_info(8) == (8, 8)
    d.graphics(('font', 8, 1))
    d.graphics(('text', 0, 0, 'A'))
    assert d.framebuffer.get_pixel(0, 0) == (0, 255, 0, 255)

@pytest.mark.parametrize("number", [1, 6, 7, 17])
def test_reserved_or_invalid_fonts_rejected(number):
    with pytest.raises(BasicError, match="no redefinible"):
        BasicMachine(f"DEFINEFONT #{number}\n01410808\nEND DEFINEFONT")

def test_concatenated_hex_words():
    cmd, _ = run_font("DEFINEFONT #9\n014108080000008000000000\nEND DEFINEFONT")
    assert cmd[-1] == bytes.fromhex("8000000000000000")

def test_header_only_declaration_allowed():
    cmd, d = run_font("DEFINEFONT #9\n01410808\nEND DEFINEFONT")
    assert cmd[-1] == b''
    d.graphics(('font', 9, 1))
    d.graphics(('text', 0, 0, 'A'))
    assert d.framebuffer.get_pixel(0, 0) == (0, 0, 0, 255)

def test_excess_words_are_accepted_but_not_exposed():
    cmd, _ = run_font("DEFINEFONT #9\n01410808\n" + "FFFFFFFF" * 5 + "\nEND DEFINEFONT")
    assert len(cmd[-1]) == 8

def test_hex_word_adjacent_to_comment():
    cmd, _ = run_font("DEFINEFONT #9\n01410808' cabecera\n00000080' mapa\n00000000\nEND DEFINEFONT")
    assert len(cmd[-1]) == 8

def test_nonbyte_aligned_rows_are_contiguous():
    # 3x3 = 9 bits. Bits 0 and 8 on; bit 8 belongs to third row.
    cmd, d = run_font("DEFINEFONT #9\n01410303\n00008080\nEND DEFINEFONT")
    # La cabecera codifica WIDTH=3 HEIGHT=3 FIRST=65 COUNT=1.
    assert cmd[2:5] == (3, 3, 65)
    d.graphics(('font', 9, 1))
    d.graphics(('text', 0, 0, 'A'))
    assert d.framebuffer.get_pixel(0, 0) == (0, 255, 0, 255)
