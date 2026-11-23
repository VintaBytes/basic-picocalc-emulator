"""Regresiones de la alineacion vertical de FONT 7 en el borde LCD."""
from basic_cde.devices.display import BitmapDisplay
from basic_cde.devices.font6x8 import GLYPHS_6X8


def test_font7_cell_keeps_last_row_clear():
    assert all(len(rows) == 8 and rows[7] == 0 for rows in GLYPHS_6X8)
    assert GLYPHS_6X8[ord('F') - 32][0] != 0


def test_font7_footer_on_bottom_edge_does_not_draw_on_last_two_pixels():
    display = BitmapDisplay()
    display.graphics(('font', 7, 2))
    display.graphics(('color', 0x000000, 0x00FF00))
    display.graphics(('text', 0, 304, 'F1: MENU'))
    fb = display.framebuffer
    # Ambas ultimas filas pertenecen al fondo del propio glifo.
    for y in (318, 319):
        for x in range(8 * 12):
            assert fb.get_pixel(x, y)[:3] == (0, 255, 0)
    # La penultima fila de glifo si tiene trazos negros: no se perdio texto.
    assert any(fb.get_pixel(x, y)[:3] == (0, 0, 0)
               for x in range(12) for y in range(304, 318))


def test_font7_explicit_bottom_background_is_preserved():
    display = BitmapDisplay()
    display.graphics(('font', 7, 1))
    display.graphics(('color', 0xFFFFFF, 0x000000))
    display.graphics(('text', 0, 312, '9'))
    assert all(display.framebuffer.get_pixel(x, 319)[:3] == (0, 0, 0)
               for x in range(6))
    assert any(display.framebuffer.get_pixel(x, y)[:3] == (255, 255, 255)
               for x in range(6) for y in range(312, 319))
