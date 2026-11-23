"""Pruebas del lector de fuentes ROM, sin codigo C ejecutado ni Qt."""
import pytest

from basic_cde.devices.rom_fonts import DIMENSIONS, parse_c_source, RomFont
from basic_cde.devices.display import BitmapDisplay


DECLS = {
    1: 'unsigned char font1[]',
    2: 'unsigned char Misc_12x20_LE[9999]',
    3: 'unsigned char Hom_16x24_LE[9999]',
    4: 'unsigned char Fnt_10x16[9999]',
    5: 'int Inconsola[9999]',
    6: 'unsigned char ArialNumFontPlus[9999] PROGMEM',
    7: 'unsigned char F_6x8_LE[9999]',
    8: 'uint32_t TinyFont[]',
}


def make_c_font(number):
    width, height = DIMENSIONS[number]
    # Solo una celda de prueba, codigo ASCII 'A', con un pixel superior izq.
    count = 4 if number == 8 else 1  # 4x6 requiere cuatro glifos para alinear palabras.
    data = bytearray([width, height, 65, count])
    data.extend([0x80] + [0] * ((width * height * count // 8) - 1))
    if number in (5, 8):
        assert len(data) % 4 == 0
        words = [int.from_bytes(data[i:i + 4], 'little')
                 for i in range(0, len(data), 4)]
        payload = ', '.join(f'0x{n:08x}' for n in words)
    else:
        payload = ', '.join(f'0x{n:02x}' for n in data)
    return f'// const bogus[]={{0x01}};\nconst {DECLS[number]}={{ {payload} }};'


@pytest.mark.parametrize('number', range(1, 9))
def test_all_eight_original_storage_formats(number):
    font = parse_c_source(make_c_font(number), number)
    assert (font.width, font.height, font.first, font.count) == (*DIMENSIONS[number], 65, 4 if number == 8 else 1)
    assert font.pixel(65, 0, 0)
    assert not font.pixel(65, 1, 0)
    assert not font.pixel(66, 0, 0)


def test_original_font_is_selected_over_provisional_bitmap():
    display = BitmapDisplay()
    display.rom_fonts[7] = parse_c_source(make_c_font(7), 7)
    display.glyph(12, 22, 'A', font=7, background=0)
    assert display.framebuffer.get_pixel(12, 22) == (0, 255, 0, 255)
    assert display.framebuffer.get_pixel(13, 22) == (0, 0, 0, 255)


def test_extended_characters_and_incomplete_font_ranges():
    font = RomFont(8, 12, 32, 224, bytes([0xff] * (12 * 224)))
    assert font.pixel(250, 0, 0)
    assert not font.pixel(31, 0, 0)
    assert not font.pixel(256, 0, 0)
    special = RomFont(32, 50, 48, 11, bytes([0xff] * (200 * 11)))
    assert special.pixel(ord('0'), 0, 0)
    assert not special.pixel(ord('A'), 0, 0)


def test_bad_dimensions_and_bad_length_are_rejected():
    with pytest.raises(ValueError, match='dimensiones'):
        parse_c_source(make_c_font(1), 2)
    with pytest.raises(ValueError, match='bytes'):
        parse_c_source('const unsigned char font1[]={0x08,0x0c,0x20,0xe0};', 1)
