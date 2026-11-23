"""Trazabilidad del entorno Linux; nunca escribe en el framebuffer BASIC.

Es metadata sobre los archivos anfitriones; no forma parte del lenguaje MMBasic.
"""
from pathlib import Path


def describe_program(path, drives=None):
    """Devuelve unidad/ruta virtual y ruta absoluta real cuando se conoce."""
    if path is None:
        return 'memoria (sin archivo asociado)'
    resolved = Path(path).expanduser().resolve(strict=False)
    if drives is not None:
        for letter in ('A', 'B'):
            root = drives.roots.get(letter)
            if root is not None and resolved.is_relative_to(root):
                part = resolved.relative_to(root).as_posix()
                return f'{letter}:/{part}  [{resolved}]'
    return str(resolved)


def run_trace(kind, path, drives=None):
    return f'[BASIC PicoCalc Emulator] {kind}: {describe_program(path, drives)}\n'
