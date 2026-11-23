"""Decodificacion de imagenes para LOAD JPG, LOAD PNG y LOAD IMAGE, sin Qt.

Las rutas las valida la unidad virtual; Pillow solo procesa bytes del fichero.
"""
from io import BytesIO
from pathlib import Path

from basic_cde.core.expressions import BasicError


def decode_image(filename: Path, fmt: str):
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise BasicError('LOAD JPG: falta Pillow') from exc
    try:
        # Cargar en memoria evita que la libreria mantenga manejadores abiertos
        # durante las operaciones del interprete.
        raw = filename.read_bytes()
        with Image.open(BytesIO(raw)) as image:
            if fmt == 'JPG':
                if image.format != 'JPEG':
                    raise BasicError('LOAD JPG: formato JPEG invalido')
                if image.info.get('progressive') or image.info.get('progression'):
                    raise BasicError('LOAD JPG: JPEG progresivo no disponible')
            elif fmt == 'PNG':
                if image.format != 'PNG':
                    raise BasicError('LOAD PNG: formato PNG invalido')
            elif image.format != 'BMP':
                raise BasicError('LOAD IMAGE: formato BMP invalido')
            # No reescalar ni convertir a paleta RGB121 aun: formato interno RGBA.
            frame = image.convert('RGBA')
            return frame.width, frame.height, frame.tobytes()
    except (OSError, ValueError, UnidentifiedImageError, MemoryError) as exc:
        raise BasicError(f'LOAD {fmt}: no se pudo leer imagen: {exc}') from exc


def apply_png_transparency(rgba: bytes, transparent=0, alphacut=20) -> bytes:
    """Mapea alfa baja a RGB121 o lo conserva como píxel no escrito.

    Transparencia en PicoMite 6.00.03: alfa estrictamente inferior a
    alphacut. El modo -1 preserva el destino del framebuffer.
    """
    transparent, alphacut = int(transparent), int(alphacut)
    if not -1 <= transparent <= 15 or not 0 <= alphacut <= 255:
        raise BasicError('LOAD PNG: argumentos de transparencia invalidos')
    rgb121 = (255 if transparent & 8 else 0,
              ((transparent >> 1) & 3) * 85,
              255 if transparent & 1 else 0)
    pixels = bytearray(rgba)
    for offset in range(0, len(pixels), 4):
        if pixels[offset + 3] < alphacut:
            if transparent == -1:
                pixels[offset + 3] = 0
            else:
                pixels[offset:offset + 4] = bytes((*rgb121, 255))
        else:
            pixels[offset + 3] = 255
    return bytes(pixels)
