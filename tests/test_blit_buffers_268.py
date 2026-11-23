"""Regresiones BLIT READ/WRITE/LOAD/CLOSE 6.00.03."""
import pytest
from PIL import Image
from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives


def execute(program, drives=None):
    session = BasicSession(program, drives=drives)
    for _ in range(100):
        step = session.step()
        if step.state == 'finished':
            return session
    pytest.fail('No termina')


def test_read_write_restores_pixels_after_cls():
    program = '''CLS RGB(0,0,0)
BOX 10,10,4,3,,RGB(240,20,60),RGB(240,20,60)
BLIT READ #1,10,10,4,3
CLS RGB(0,0,0)
BLIT WRITE #1,60,65
BLIT CLOSE #1
END'''
    s=execute(program)
    assert s.display.framebuffer.get_pixel(60,65)[:3] == (240,20,60)
    assert s.display.framebuffer.get_pixel(63,67)[:3] == (240,20,60)
    assert s.display.framebuffer.get_pixel(10,10)[:3] == (0,0,0)
    assert not s.display.blit_buffers


def test_read_multiple_buffers_independent():
    program = '''CLS RGB(0,0,0)
PIXEL 2,2,RGB(30,120,200)
BLIT READ 1,2,2,1,1
PIXEL 2,2,RGB(250,80,40)
BLIT READ #2,2,2,1,1
BLIT WRITE 1,5,5
BLIT WRITE 2,6,6
END'''
    s=execute(program)
    assert s.display.framebuffer.get_pixel(5,5)[:3] == (30,120,200)
    assert s.display.framebuffer.get_pixel(6,6)[:3] == (250,80,40)


def test_read_and_write_in_f_plan():
    program='''FRAMEBUFFER CREATE
FRAMEBUFFER WRITE F
PIXEL 9,9,RGB(255,5,10)
BLIT READ #1,9,9,1,1
CLS
BLIT WRITE #1,4,4
FRAMEBUFFER COPY F,N
END'''
    s=execute(program)
    assert s.display.framebuffer.get_pixel(4,4)[:3] == (255,5,10)


def test_blit_write_partial_and_clip():
    s=execute('''BOX 1,1,3,3,,RGB(40,80,120),RGB(40,80,120)
BLIT READ #3,1,1,3,3
BLIT WRITE #3,318,319,2,2
END''')
    assert s.display.framebuffer.get_pixel(319,319)[:3] == (40,80,120)


def test_load_bmp_from_virtual_unit(tmp_path):
    image=Image.new('RGB',(5,4),(1,2,3))
    image.putpixel((2,1),(99,170,201))
    image.save(tmp_path/'tile.bmp')
    s=execute('BLIT LOAD #7,"tile.bmp",2,1,2,2\nBLIT WRITE #7,80,90\nEND',VirtualDrives(a=tmp_path))
    assert s.display.framebuffer.get_pixel(80,90)[:3] == (99,170,201)
    assert s.display.framebuffer.get_pixel(81,91)[:3] == (1,2,3)


@pytest.mark.parametrize('source', [
    'BLIT READ #33,0,0,1,1',
    'BLIT READ #1,319,319,4,4',
    'BLIT WRITE #1,10,10',
    'BLIT CLOSE #1',
    'BLIT READ #1,0,0,2,2\nBLIT READ #1,0,0,2,2',
    'BLIT READ #1,0,0,2,2\nBLIT WRITE #1,0,0,3,3',
])
def test_invalid_buffers_produce_errors(source):
    session=BasicSession(source)
    with pytest.raises(BasicError):
        for _ in range(10):
            step=session.step()
            if step.state == 'finished':
                break
