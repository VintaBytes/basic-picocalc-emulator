"""Geometria del skin PicoCalc, independiente de Qt y del interprete.

El monitor MMBasic sigue siendo exactamente 320x320: solo se superpone
sobre una fotografia con fondo transparente.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

PHOTO_SIZE_VERTICAL = (840, 1300)
PHOTO_SIZE_HORIZONTAL = (1479, 648)
# x, y, ancho, alto de la zona sobre la carcasa en coordenadas de la foto.
# Movida 18 px hacia arriba respecto del primer skin (v0.2.39).
SCREEN_RECT_VERTICAL = (126, 112, 555, 555)
# Pequenio LED junto al marco del LCD.
LED_CENTER_VERTICAL = (705, 171)

# Alias historicos para pruebas y codigo previo.
PHOTO_SIZE = PHOTO_SIZE_VERTICAL
SCREEN_RECT = SCREEN_RECT_VERTICAL


@dataclass(frozen=True)
class SkinLayout:
    host_width: int
    host_height: int
    screen_x: int
    screen_y: int
    screen_side: int
    orientation: str


def skin_asset_path() -> str:
    """PNG RGBA empaquetado. No requiere Pillow ni Internet al ejecutar."""
    return str(Path(resources.files('basic_cde.gui') / 'assets' / 'picocalc-transparent.png'))


# La vista horizontal es una composición de dos recortes derechos, no una
# rotación de la foto: marco de pantalla a la izquierda, teclado a la derecha.
HORIZONTAL_SCREEN_CROP = (45, 40, 785, 688)
HORIZONTAL_KEYBOARD_CROP = (59, 690, 778, 1270)
HORIZONTAL_KEYBOARD_ORIGIN = (760, 35)


def screen_point_horizontal(point: tuple[int, int]) -> tuple[int, int]:
    x, y = point
    crop_x, crop_y, _, _ = HORIZONTAL_SCREEN_CROP
    return (x - crop_x, y - crop_y)


def keyboard_point_horizontal(point: tuple[int, int]) -> tuple[int, int]:
    x, y = point
    crop_x, crop_y, _, _ = HORIZONTAL_KEYBOARD_CROP
    origin_x, origin_y = HORIZONTAL_KEYBOARD_ORIGIN
    return (origin_x + x - crop_x, origin_y + y - crop_y)


def photo_size_for_mode(orientation: str) -> tuple[int, int]:
    if orientation == 'horizontal':
        return PHOTO_SIZE_HORIZONTAL
    return PHOTO_SIZE_VERTICAL


def screen_rect_for_mode(orientation: str) -> tuple[int, int, int, int]:
    if orientation == 'horizontal':
        x, y, w, h = SCREEN_RECT_VERTICAL
        px, py = screen_point_horizontal((x, y))
        return (px, py, w, h)
    return SCREEN_RECT_VERTICAL


def led_center_for_mode(orientation: str) -> tuple[int, int]:
    if orientation == 'horizontal':
        return screen_point_horizontal(LED_CENTER_VERTICAL)
    return LED_CENTER_VERTICAL


def horizontal_skin_asset_path() -> str:
    return str(Path(resources.files('basic_cde.gui') / 'assets' / 'picocalc-horizontal.png'))


def layout_for_mode(orientation: str = 'vertical', screen_side: int = 320) -> SkinLayout:
    """Ajusta la foto hasta mostrar exactamente screen_side pixeles LCD."""
    screen_side = int(screen_side)
    if screen_side <= 0:
        raise ValueError('screen_side debe ser positivo')
    rect_x, rect_y, rect_w, _ = screen_rect_for_mode(orientation)
    scale = screen_side / rect_w
    photo_w, photo_h = photo_size_for_mode(orientation)
    return SkinLayout(
        host_width=round(photo_w * scale),
        host_height=round(photo_h * scale),
        screen_x=round(rect_x * scale),
        screen_y=round(rect_y * scale),
        screen_side=screen_side,
        orientation=orientation,
    )


def layout_for_screen(screen_side: int = 320) -> SkinLayout:
    """Compatibilidad historica: skin vertical a 1x real."""
    return layout_for_mode('vertical', screen_side)
