"""Regresiones para el framebuffer y su motor sin dependencia Qt."""
from basic_cde.devices.display import BitmapDisplay
from basic_cde.core.machine import BasicMachine


def test_console_draws_on_bitmap_and_keeps_black_background():
    display = BitmapDisplay()
    original = display.framebuffer.snapshot()
    display.console('A')
    assert display.framebuffer.snapshot() != original
    assert display.framebuffer.get_pixel(319, 319) == (0, 0, 0, 255)


def test_line_with_zero_length_writes_one_pixel():
    display = BitmapDisplay()
    display.line(10, 12, 10, 12, 0x12ABCD)
    assert display.framebuffer.get_pixel(10, 12) == (18, 171, 205, 255)


def test_cls_resets_cursor_and_clears_previous_graphics():
    display = BitmapDisplay()
    display.console('A\nB\n')
    display.graphics(('cls', 0x102030))
    assert (display.col, display.row) == (0, 0)
    assert display.framebuffer.get_pixel(1, 1) == (16, 32, 48, 255)


def test_scroll_after_blank_lines_never_loses_text():
    display = BitmapDisplay()
    display.console('\n' * 40 + 'A')
    assert display.row == 25
    assert display.framebuffer.snapshot().count(bytes((0,255,0,255))) > 0


def test_text_and_pixel_share_one_framebuffer():
    display = BitmapDisplay()
    display.graphics(('text', 4, 2, 'A'))
    display.graphics(('pixel', 319, 319, 0xFF0000))
    assert display.framebuffer.get_pixel(319, 319) == (255, 0, 0, 255)
    assert display.framebuffer.snapshot().count(bytes((0,255,0,255))) > 0


def test_machine_emits_graphical_operations_without_qt():
    machine = BasicMachine('COLOR RGB(255,0,0), RGB(0,0,0)\nCLS\nPIXEL 200,200,RGB(0,255,0)\nTEXT 4,5,"OK"\nPRINT "HOLA"\nEND')
    commands = []
    text = []
    for _ in range(10):
        result = machine.step()
        if result.graphics: commands.append(result.graphics)
        if result.output: text.append(result.output)
        if result.state == 'finished': break
    assert [cmd[0] for cmd in commands] == ['color', 'cls', 'pixel', 'text']
    assert text == ['HOLA\n']
    d = BitmapDisplay()
    for cmd in commands: d.graphics(cmd)
    d.console(''.join(text))
    assert d.framebuffer.get_pixel(200,200) == (0,255,0,255)
