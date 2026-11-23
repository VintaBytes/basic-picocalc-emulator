"""Mapa del teclado fotografiado (coordenadas de la foto de 840 x 1300).

Este fichero no importa Qt. Las entradas son las mismas teclas BASIC de
PicoCalc que recibe el teclado anfitrion; no se cambia el interprete.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from basic_cde.gui.skin import PHOTO_SIZE_VERTICAL, keyboard_point_horizontal


Point = tuple[int, int]


@dataclass(frozen=True)
class KeyZone:
    name: str
    x: int
    y: int
    width: int
    height: int
    polygon: tuple[Point, ...] = field(default_factory=tuple)

    def contains(self, x: float, y: float) -> bool:
        if self.polygon:
            return _point_in_polygon(x, y, self.polygon)
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        if not self.polygon:
            return (self.x, self.y, self.width, self.height)
        xs = [p[0] for p in self.polygon]
        ys = [p[1] for p in self.polygon]
        return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _point_in_polygon(x: float, y: float, polygon: tuple[Point, ...]) -> bool:
    inside = False
    points = list(polygon)
    if len(points) < 3:
        return False
    x1, y1 = points[-1]
    for x2, y2 in points:
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1):
            inside = not inside
        x1, y1 = x2, y2
    return inside


def _tri_points(kind: str, x: int, y: int, width: int, height: int) -> tuple[Point, ...]:
    if kind == 'up':
        return ((x + width // 2, y), (x + width, y + height * 3 // 5),
                (x + width * 3 // 4, y + height), (x + width // 4, y + height),
                (x, y + height * 3 // 5))
    if kind == 'down':
        return ((x + width // 4, y), (x + width * 3 // 4, y),
                (x + width, y + height * 2 // 5), (x + width // 2, y + height),
                (x, y + height * 2 // 5))
    if kind == 'left':
        return ((x, y + height // 2), (x + width * 2 // 5, y),
                (x + width, y + height // 4), (x + width, y + height * 3 // 4),
                (x + width * 2 // 5, y + height))
    if kind == 'right':
        return ((x, y + height // 4), (x + width * 3 // 5, y),
                (x + width, y + height // 2), (x + width * 3 // 5, y + height),
                (x, y + height * 3 // 4))
    raise ValueError(kind)


def keyboard_zones() -> tuple[KeyZone, ...]:
    zones: list[KeyZone] = [
        KeyZone('Up', 141, 702, 93, 61, _tri_points('up', 141, 702, 93, 61)),
        KeyZone('Left', 116, 759, 65, 75, _tri_points('left', 116, 759, 65, 75)),
        KeyZone('Right', 191, 759, 65, 75, _tri_points('right', 191, 759, 65, 75)),
        KeyZone('Down', 140, 808, 93, 45, _tri_points('down', 140, 808, 93, 45)),
    ]
    for i in range(1, 6):
        zones.append(KeyZone(f'F{i}', 294 + (i - 1) * 90, 706, 72, 52))
    for i, key in enumerate(('Esc', 'Tab', 'CapsLock', 'Delete', 'Backspace')):
        zones.append(KeyZone(key, 294 + i * 90, 768, 72, 49))
    for i, key in enumerate(('`', '/', '\\', '-', '=', '[', ']')):
        zones.append(KeyZone(key, 295 + i * 63, 818, 55, 50))
    for i, key in enumerate('1234567890'):
        zones.append(KeyZone(key, 105 + i * 63, 880, 56, 54))
    for i, key in enumerate('QWERTYUIOP'):
        zones.append(KeyZone(key, 105 + i * 63, 945, 56, 51))
    for i, key in enumerate('ASDFGHJKL'):
        zones.append(KeyZone(key, 105 + i * 63, 1010, 56, 54))
    for i, key in enumerate('ZXCVBNM,.'):
        zones.append(KeyZone(key, 105 + i * 63, 1077, 56, 54))
    zones.extend((
        KeyZone('Enter', 670, 1010, 67, 126),
        KeyZone('ShiftLeft', 112, 1147, 90, 61),
        KeyZone('Ctrl', 214, 1147, 62, 61),
        KeyZone('Alt', 283, 1147, 56, 61),
        KeyZone('Space', 348, 1147, 144, 61),
        KeyZone(';', 499, 1147, 58, 61),
        KeyZone("'", 561, 1147, 65, 61),
        KeyZone('ShiftRight', 634, 1147, 96, 61),
    ))
    return tuple(zones)


def horizontal_zone(zone: KeyZone) -> KeyZone:
    x, y = keyboard_point_horizontal((zone.x, zone.y))
    polygon = tuple(keyboard_point_horizontal(p) for p in zone.polygon)
    return KeyZone(zone.name, x, y, zone.width, zone.height, polygon)


KEY_ZONES_VERTICAL = keyboard_zones()
KEY_ZONES_HORIZONTAL = tuple(horizontal_zone(zone) for zone in KEY_ZONES_VERTICAL)
KEY_ZONES = KEY_ZONES_VERTICAL


def key_zones(orientation: str = 'vertical') -> tuple[KeyZone, ...]:
    return KEY_ZONES_HORIZONTAL if orientation == 'horizontal' else KEY_ZONES_VERTICAL


def key_at(x: float, y: float, orientation: str = 'vertical') -> str | None:
    """Devuelve tecla tocada por un clic en coordenadas de la foto original."""
    for zone in key_zones(orientation):
        if zone.contains(x, y):
            return zone.name
    return None


def visual_key_for_host(key: int, text: str, *, qt_f1: int, qt_a: int,
                        qt_0: int, qt_1: int) -> str | None:
    """Mapa mínimo de códigos Qt a zonas fotográficas sin depender de Qt."""
    if qt_f1 <= key <= qt_f1 + 9:
        return 'F' + str(1 + ((key - qt_f1) % 5))
    if qt_a <= key <= qt_a + 25:
        return chr(ord('A') + key - qt_a)
    if qt_0 <= key <= qt_0 + 9:
        return chr(ord('0') + key - qt_0)
    if text in ('`', '/', '\\', '-', '=', '[', ']', ',', '.', ';', "'"):
        return text
    return None
