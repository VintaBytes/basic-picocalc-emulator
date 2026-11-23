"""Render provisional del INPUT sobre una copia de la pantalla, sin Qt."""
from basic_cde.devices.display import BitmapDisplay


def input_anchor(display):
    return (display.framebuffer.snapshot(), display.col, display.row,
            display.current_font, display.font_scale, display.foreground,
            display.background, dict(display.fonts))


def input_preview(anchor, draft):
    pixels, col, row, font, scale, fg, bg, fonts = anchor
    preview = BitmapDisplay()
    preview.framebuffer.pixels[:] = pixels
    preview.col, preview.row = col, row
    preview.current_font, preview.font_scale = font, scale
    preview.foreground, preview.background = fg, bg
    preview.fonts = fonts
    preview.console(draft + '_')
    return preview.framebuffer.snapshot()
