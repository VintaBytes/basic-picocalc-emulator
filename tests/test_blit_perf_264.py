"""BLIT compatible with the self-overlapping scrolling in demo.bas."""
from basic_cde.app.session import BasicSession
from basic_cde.devices.display import BitmapDisplay
from basic_cde.devices.framebuffer import Framebuffer


def test_blit_overlap_down_and_up():
    f = Framebuffer(4, 5)
    for y in range(5):
        for x in range(4):
            f.pixel(x, y, y * 10, x, 0)
    f.blit(0, 0, 0, 1, 4, 4)
    assert [f.get_pixel(0, y)[0] for y in range(5)] == [0, 0, 10, 20, 30]
    f.blit(0, 1, 0, 0, 4, 4)
    assert [f.get_pixel(0, y)[0] for y in range(5)] == [0, 10, 20, 30, 30]


def test_blit_clip_and_target_offscreen():
    d = BitmapDisplay(8, 8)
    d.graphics(('framebuffer', 'CREATE'))
    d.graphics(('framebuffer', 'WRITE', 'F'))
    d.graphics(('pixel', 1, 1, 0x123456))
    d.graphics(('blit', 1, 1, 2, 2, 6, 6))
    assert d.buffers['F'].get_pixel(2, 2)[:3] == (0x12, 0x34, 0x56)
    assert d.framebuffer.get_pixel(2, 2)[:3] == (0, 0, 0)
    d.graphics(('framebuffer', 'COPY', 'F', 'N'))
    assert d.framebuffer.get_pixel(2, 2)[:3] == (0x12, 0x34, 0x56)


def test_blit_demo_p9_exact_command_and_visible_copy():
    source = '''FRAMEBUFFER CREATE
FRAMEBUFFER WRITE F
CLS RGB(0,0,0)
PIXEL 2,2,RGB(255,0,0)
BLIT 0,0,0,200,320,20:BLIT 0,20,0,0,320,220
FRAMEBUFFER COPY F,N
END'''
    session = BasicSession(source)
    for _ in range(30):
        result = session.step()
        if result.state == 'finished':
            break
        assert result.state != 'error', result
    else:
        raise AssertionError('BASIC sin terminar')
    assert session.display.framebuffer.get_pixel(2, 182)[:3] == (255, 0, 0)


def test_blit_horizontal_overlap_snapshot():
    f = Framebuffer(6, 1)
    for x in range(6):
        f.pixel(x, 0, x + 10, 0, 0)
    f.blit(0, 0, 2, 0, 4, 1)
    assert [f.get_pixel(x, 0)[0] for x in range(6)] == [10, 11, 10, 11, 12, 13]


def test_circle_filled_and_box_cropped():
    d = BitmapDisplay(32, 32)
    d.graphics(('box', -3, -3, 8, 8, 0, None, 0x123456))
    assert d.framebuffer.get_pixel(0, 0)[:3] == (0x12, 0x34, 0x56)
    d.graphics(('circle', 12, 12, 5, 1, 1, 0xABCDEF, 0x010203))
    assert d.framebuffer.get_pixel(12, 12)[:3] == (1, 2, 3)
    assert d.framebuffer.get_pixel(17, 12)[:3] == (0xAB, 0xCD, 0xEF)
