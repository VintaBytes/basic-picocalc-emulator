"""Las 8 fuentes autenticas van incluidas en el paquete, sin red ni instalacion."""
import zlib
from importlib.resources import files

from basic_cde.devices.display import BitmapDisplay
from basic_cde.devices.rom_fonts import DIMENSIONS, bundled_fonts, decode_rle

EXPECTED = {
    1: (2692, 0xE7DE0137), 2: (2854, 0x0F320D4E),
    3: (4564, 0x79F259CD), 4: (4484, 0x58FACE4A),
    5: (9124, 0x1E88CFF2), 6: (2204, 0xFB0F5401),
    7: (580, 0x29639447), 8: (292, 0x24928685),
}


def test_all_eight_original_fonts_are_bundled_and_exact():
    fonts = bundled_fonts()
    assert set(fonts) == set(range(1, 9))
    for number, (length, checksum) in EXPECTED.items():
        data = files('basic_cde.devices').joinpath('font_data', f'font{number}.rle').read_bytes()
        raw = decode_rle(data)
        assert len(raw) == length
        assert zlib.adler32(raw) == checksum
        assert (fonts[number].width, fonts[number].height) == DIMENSIONS[number]


def test_font_6_is_numeric_only():
    font = bundled_fonts()[6]
    assert font.first == ord('0')
    assert font.count == 11
    assert not any(font.pixel(ord('A'), x, y) for x in range(font.width) for y in range(font.height))
    d = BitmapDisplay()
    d.graphics(('font', 6, 1))
    d.console('0')
    assert any(d.framebuffer.get_pixel(x, y)[:3] != (0,0,0)
               for x in range(32) for y in range(50))
