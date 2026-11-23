"""Regresiones del borrado y del fondo de TEXT en Sokoban."""

from basic_cde.devices.display import BitmapDisplay


def sokoban_font(display):
    """Un sprite 8x8 sintético cuyo primer píxel está encendido."""
    data = bytes([0x80] + [0] * 7)
    display.graphics(('definefont', 10, 8, 8, ord('j'), data))
    display.graphics(('font', 10, 1))


def test_text_default_background_overwrites_existing_pixels():
    display = BitmapDisplay()
    sokoban_font(display)
    display.graphics(('color', 0xB3CDB3, 0x4F4F7F))
    display.graphics(('text', 16, 24, 'j'))
    assert display.framebuffer.get_pixel(16, 24) == (179, 205, 179, 255)
    assert display.framebuffer.get_pixel(17, 24) == (79, 79, 127, 255)

    # Sokoban borra el tile anterior con cuatro espacios sobre negro.
    display.graphics(('color', 0x000000, 0x000000))
    for x, y in ((16, 24), (24, 24), (16, 32), (24, 32)):
        display.graphics(('text', x, y, ' '))
    for y in range(24, 40):
        for x in range(16, 32):
            assert display.framebuffer.get_pixel(x, y) == (0, 0, 0, 255)


def test_text_background_minus_one_keeps_existing_pixels():
    display = BitmapDisplay()
    sokoban_font(display)
    display.graphics(('cls', 0x112233))
    display.graphics(('color', 0xABCDEF, 0x445566))
    display.graphics(('text', 10, 11, 'j', 'LT', 10, 1, 0xFFEEDD, -1))
    assert display.framebuffer.get_pixel(10, 11) == (255, 238, 221, 255)
    assert display.framebuffer.get_pixel(11, 11) == (17, 34, 51, 255)


def test_text_explicit_background_takes_precedence_over_colour():
    display = BitmapDisplay()
    sokoban_font(display)
    display.graphics(('color', 0xFFFFFF, 0x000000))
    display.graphics(('text', 0, 0, 'j', 'LT', 10, 1, 0xFFFFFF, 0x123456))
    assert display.framebuffer.get_pixel(1, 0) == (18, 52, 86, 255)


def test_player_moves_without_leaving_old_sprite():
    display = BitmapDisplay()
    sokoban_font(display)
    display.graphics(('color', 0xB3CDB3, 0x4F4F7F))
    display.graphics(('text', 0, 0, 'j'))
    display.graphics(('color', 0, 0))
    display.graphics(('text', 0, 0, ' '))
    display.graphics(('color', 0xB3CDB3, 0x4F4F7F))
    display.graphics(('text', 16, 0, 'j'))
    assert display.framebuffer.get_pixel(0, 0) == (0, 0, 0, 255)
    assert display.framebuffer.get_pixel(16, 0) == (179, 205, 179, 255)
