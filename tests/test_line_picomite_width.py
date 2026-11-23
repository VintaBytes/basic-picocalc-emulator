"""Regresion PicoMite: LINE gruesa positiva anclada, negativa centrada.

Bug detectado con PIPE.BAS 0.1.8 en PicoCalc real: el emulador
centraba siempre los trazos de grosor 4 u 8, a diferencia del hardware.
"""
from basic_cde.devices.display import BitmapDisplay


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def pixel(display, x, y):
    return display.framebuffer.get_pixel(x, y)[:3]


def test_horizontal_positive_width_extends_below_reference_line():
    display = BitmapDisplay(32, 32)
    display.line(5, 10, 12, 10, color=0xFFFFFF, thickness=4)
    assert pixel(display, 5, 10) == WHITE
    assert pixel(display, 12, 13) == WHITE
    assert pixel(display, 5, 9) == BLACK
    assert pixel(display, 12, 14) == BLACK


def test_vertical_positive_width_extends_right_of_reference_line():
    display = BitmapDisplay(32, 32)
    display.line(10, 5, 10, 12, color=0xFFFFFF, thickness=8)
    assert pixel(display, 10, 5) == WHITE
    assert pixel(display, 17, 12) == WHITE
    assert pixel(display, 9, 5) == BLACK
    assert pixel(display, 18, 12) == BLACK


def test_negative_width_retains_centered_picomite_lines():
    display = BitmapDisplay(32, 32)
    display.line(5, 10, 12, 10, color=0xFFFFFF, thickness=-4)
    assert pixel(display, 5, 8) == WHITE
    assert pixel(display, 12, 11) == WHITE
    assert pixel(display, 5, 7) == BLACK
    assert pixel(display, 12, 12) == BLACK


def test_one_pixel_line_and_backward_coordinates():
    display = BitmapDisplay(32, 32)
    display.line(12, 10, 5, 10, color=0xFFFFFF, thickness=1)
    assert pixel(display, 5, 10) == WHITE
    assert pixel(display, 12, 10) == WHITE
    assert pixel(display, 5, 9) == BLACK
    assert pixel(display, 12, 11) == BLACK
