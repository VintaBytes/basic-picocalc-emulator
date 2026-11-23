"""Bitmap de fuentes PicoMite a partir de datos .h, sin ejecutar codigo C.

Las cabeceras del firmware se tratan exclusivamente como tablas de bits.
No se importa ni se ejecuta el interprete MMBasic.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SOURCES = {
    1: '01-font1.h',
    2: '02-Misc_12x20_LE.h',
    3: '03-Hom_16x24_LE.h',
    4: '04-Fnt_10x16.h',
    5: '05-Inconsola.h',
    6: '06-ArialNumFontPlus.h',
    7: '07-Font_8x6.h',
    8: '08-smallfont.h',
}
WORD_FONTS = {5, 8}  # Los arrays C son uint32_t en orden little endian.
DIMENSIONS = {1: (8, 12), 2: (12, 20), 3: (16, 24), 4: (10, 16),
              5: (24, 32), 6: (32, 50), 7: (6, 8), 8: (4, 6)}


@dataclass(frozen=True)
class RomFont:
    width: int
    height: int
    first: int
    count: int
    data: bytes

    def pixel(self, character: int, x: int, y: int) -> bool:
        if not self.first <= character < self.first + self.count:
            # No inventamos glifos faltantes en fuentes parciales (FONT 6).
            return False
        index = ((character - self.first) * self.width * self.height) + y * self.width + x
        return bool(self.data[index // 8] & (0x80 >> (index % 8)))


def parse_c_source(text: str, number: int) -> RomFont:
    """Interpreta los enteros de una matriz C de fuente, con validacion estricta.

    Ignora comentarios (incluso arrays comentados) y macros. No evalua
    expresiones, ni permite incluir instrucciones C en el motor Python.
    """
    if number not in SOURCES:
        raise ValueError(f'Fuente desconocida: {number}')
    without_comments = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    declaration = re.search(r'\b(?:font1|Misc_12x20_LE|Hom_16x24_LE|Fnt_10x16|Inconsola|ArialNumFontPlus|F_6x8_LE|TinyFont)\s*\[[^\]]*\]\s*(?:PROGMEM\s*)?=\s*\{', without_comments)
    if declaration is None:
        raise ValueError(f'Falta el array de glifos de FONT {number}')
    end = without_comments.find('}', declaration.end())
    if end < 0:
        raise ValueError('Falta el cierre de la tabla C')
    values = re.findall(r'0[xX][0-9a-fA-F]+|\b\d+\b', without_comments[declaration.end():end])
    numbers = [int(v, 0) for v in values]
    if number in WORD_FONTS:
        if any(not 0 <= n <= 0xFFFFFFFF for n in numbers):
            raise ValueError('Palabra de fuente fuera de rango')
        raw = b''.join(n.to_bytes(4, 'little') for n in numbers)
    else:
        if any(not 0 <= n <= 255 for n in numbers):
            raise ValueError('Byte de fuente fuera de rango')
        raw = bytes(numbers)
    if len(raw) < 4:
        raise ValueError('Cabecera de fuente incompleta')
    width, height, first, count = raw[:4]
    if (width, height) != DIMENSIONS[number]:
        raise ValueError(f'FONT {number}: dimensiones inesperadas {width}x{height}')
    expected = 4 + (width * height * count + 7) // 8
    if len(raw) != expected:
        raise ValueError(f'FONT {number}: {len(raw)} bytes, se esperaban {expected}')
    return RomFont(width, height, first, count, raw[4:])


def load_original_fonts(directory: Path) -> dict[int, RomFont]:
    """Carga las ocho cabeceras originales de las fuentes bitmap de PicoMite."""
    directory = Path(directory)
    return {number: parse_c_source((directory / filename).read_text(encoding='utf-8'), number)
            for number, filename in SOURCES.items()}


def parse_binary_font(raw: bytes, number: int) -> RomFont:
    """Lee bitmap extraido de la fuente PicoMite, incluyendo cabecera de 4 bytes."""
    if len(raw) < 4:
        raise ValueError(f'FONT {number}: datos incompletos')
    width, height, first, count = raw[:4]
    if (width, height) != DIMENSIONS[number]:
        raise ValueError(f'FONT {number}: dimensiones inesperadas')
    expected = 4 + (width * height * count + 7) // 8
    if len(raw) != expected:
        raise ValueError(f'FONT {number}: tamaño incompatible con cabecera')
    return RomFont(width, height, first, count, raw[4:])


def decode_rle(content: bytes) -> bytes:
    """Descomprime secuencia sin perdida: FF 00 n = n ceros, FF 01 = FF."""
    out = bytearray()
    index = 0
    while index < len(content):
        value = content[index]
        index += 1
        if value != 255:
            out.append(value)
            continue
        if index >= len(content):
            raise ValueError('Escape RLE incompleto')
        kind = content[index]
        index += 1
        if kind == 1:
            out.append(255)
        elif kind == 0:
            if index >= len(content) or not content[index]:
                raise ValueError('Longitud RLE invalida')
            out.extend(bytes(content[index]))
            index += 1
        else:
            raise ValueError('Escape RLE no reconocido')
    return bytes(out)


def bundled_fonts() -> dict[int, RomFont]:
    """Usa bitmaps originales incluidos offline; admite .h antiguos como respaldo."""
    from importlib.resources import files
    root = files('basic_cde.devices').joinpath('font_data')
    result = {}
    for number, name in SOURCES.items():
        try:
            data = root.joinpath(f'font{number}.rle').read_bytes()
            result[number] = parse_binary_font(decode_rle(data), number)
            continue
        except (FileNotFoundError, OSError):
            pass
        try:
            text = root.joinpath(name).read_text(encoding='utf-8')
        except (FileNotFoundError, OSError):
            continue
        result[number] = parse_c_source(text, number)
    return result
