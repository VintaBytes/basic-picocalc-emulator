"""Regression for FRAMEBUFFER merge palette and sync mode."""
import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay


def complete(program):
    session = BasicSession(program)
    for _ in range(80):
        result = session.step()
        if result.state == "error":
            raise AssertionError(result.output)
        if result.state == "finished":
            return session
    raise AssertionError("timeout")


def test_merging_index_three_uses_rgb121_cobalt_not_rgb_000003():
    display = BitmapDisplay(5, 5)
    display.framebuffer_command("CREATE")
    display.framebuffer_command("LAYER")
    display.framebuffer_command("WRITE", "F")
    display.cls(0xAA0000)
    display.framebuffer_command("WRITE", "L")
    display.cls(0x000000)
    display.graphics(("pixel", 1, 1, 0x0055FF))
    display.graphics(("pixel", 2, 2, 0x00FF00))
    display.framebuffer_command("MERGE", 3, "B")
    assert display.framebuffer.get_pixel(1, 1)[:3] == (170, 0, 0)
    assert display.framebuffer.get_pixel(2, 2)[:3] == (0, 255, 0)


def test_framebuffer_wait_synchronous_and_mergeb_parses_in_bas():
    source = """FRAMEBUFFER CREATE
FRAMEBUFFER LAYER
FRAMEBUFFER WRITE F
CLS RGB(0,0,128)
FRAMEBUFFER WRITE L
CLS 0
PIXEL 20,30,RGB(255,255,0)
FRAMEBUFFER MERGE 0,B
FRAMEBUFFER WAIT
END"""
    display = complete(source).display
    assert display.framebuffer.get_pixel(20, 30)[:3] == (255, 255, 0)
    assert display.framebuffer.get_pixel(0, 0)[:3] == (0, 0, 128)


def test_wait_rejects_parameters_and_merge_bad_mode():
    display = BitmapDisplay()
    with pytest.raises(BasicError):
        display.framebuffer_command("WAIT", "F")
    with pytest.raises(BasicError):
        display.framebuffer_command("MERGE", 0, "R")


def test_merge_existing_rgb_color_key_unchanged():
    display = BitmapDisplay(4, 4)
    display.framebuffer_command("CREATE")
    display.framebuffer_command("LAYER")
    display.framebuffer_command("WRITE", "F")
    display.cls(0xFFFFFF)
    display.framebuffer_command("WRITE", "L")
    display.cls(0x112233)
    display.graphics(("pixel", 2, 2, 0x445566))
    display.framebuffer_command("MERGE", 0x112233)
    assert display.framebuffer.get_pixel(0, 0)[:3] == (255, 255, 255)
    assert display.framebuffer.get_pixel(2, 2)[:3] == (68, 85, 102)


def test_release_demo_finishes_with_virtual_clock():
    from pathlib import Path

    class Clock:
        def __init__(self):
            self.now = 0.0

        def __call__(self):
            return self.now

    clock = Clock()
    filename = Path(__file__).parents[1] / "examples" / "framebuffer-253.bas"
    session = BasicSession(filename.read_text(encoding="ascii"), clock=clock)
    for _ in range(100):
        result = session.step()
        clock.now += 0.10
        if result.state in ("error", "finished"):
            break
    assert result.state == "finished"
    assert set(session.display.buffers) == {"N"}
    assert session.display.framebuffer.get_pixel(0, 0)[:3] == (255, 255, 0)
