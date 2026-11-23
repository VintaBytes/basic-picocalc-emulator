"""Regresiones fase 1 sprites, separada de buffers BLIT."""
import pytest
from PIL import Image
from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives


def run(source, drives=None):
    s = BasicSession(source, drives=drives)
    for _ in range(100):
        result = s.step()
        if result.state == 'finished':
            return s
    pytest.fail('El BASIC no termino')


def pixel(s,x,y):
    return s.display.framebuffer.get_pixel(x,y)[:3]


def test_read_write_close_and_rgb121():
    s = run('''CLS RGB(0,0,0)
PIXEL 7,8,RGB(245,220,245)
SPRITE READ #1,7,8,1,1
CLS
SPRITE WRITE #1,100,80
SPRITE CLOSE #1
END''')
    assert pixel(s,100,80) == (255,255,255)
    assert not s.display.sprite_buffers


def test_separate_from_blit():
    s = run('''PIXEL 2,2,RGB(255,0,0)
BLIT READ #1,2,2,1,1
SPRITE READ #1,2,2,1,1
SPRITE CLOSE ALL
BLIT WRITE #1,50,60
END''')
    assert pixel(s,50,60) == (255,0,0)
    assert 1 in s.display.blit_buffers
    assert s.display.sprite_buffers == {}


def test_sprite_mode_mirror_and_transparency():
    s = run('''CLS RGB(0,0,0)
PIXEL 0,0,RGB(255,0,0)
PIXEL 1,0,RGB(0,0,255)
SPRITE READ #1,0,0,2,1
CLS RGB(20,20,20)
SPRITE WRITE #1,20,20,5
SPRITE SET TRANSPARENT 1
SPRITE WRITE #1,30,20,5
END''')
    # modo 5 espeja horizontal y no dibuja pixeles transparentes (indice 0).
    assert pixel(s,20,20) == (0,0,255)
    assert pixel(s,21,20) == (255,0,0)
    # Al elegir azul como transparente, se conserva el fondo en x=30.
    assert pixel(s,30,20) == (20,20,20)
    assert pixel(s,31,20) == (255,0,0)


def test_sprite_png_and_bmp_loading(tmp_path):
    png = Image.new('RGBA',(2,1),(255,0,0,255))
    png.putpixel((1,0),(0,255,0,0))
    png.save(tmp_path/'a.png')
    bmp = Image.new('RGB',(3,2),(0,0,255))
    bmp.save(tmp_path/'b.bmp')
    src='''CLS RGB(50,50,50)
SPRITE LOADPNG #2,"a",0,20
SPRITE WRITE #2,30,30
SPRITE LOADBMP #3,"b",1,0,1,1
SPRITE WRITE #3,40,40
END'''
    s=run(src,VirtualDrives(a=tmp_path))
    assert pixel(s,30,30) == (255,0,0)
    assert pixel(s,31,30) == (50,50,50)
    assert pixel(s,40,40) == (0,0,255)


def test_render_in_f_before_copy():
    s=run('''FRAMEBUFFER CREATE
FRAMEBUFFER WRITE F
PIXEL 1,1,RGB(255,0,0)
SPRITE READ #2,1,1,1,1
CLS
SPRITE WRITE #2,55,56
FRAMEBUFFER COPY F,N
END''')
    assert pixel(s,55,56) == (255,0,0)


@pytest.mark.parametrize('source', [
    'SPRITE WRITE #1,1,1',
    'SPRITE CLOSE #1',
    'SPRITE READ #65,0,0,2,2',
    'SPRITE READ #1,-1,0,2,2',
    'SPRITE READ #1,0,0,1,1\nSPRITE READ #1,0,0,1,1',
    'SPRITE SET TRANSPARENT 16',
    'SPRITE READ #1,0,0,2,2\nSPRITE WRITE #1,10,10,8',
])
def test_sprite_invalid(source):
    s=BasicSession(source)
    with pytest.raises(BasicError):
        for _ in range(10):
            result=s.step()
            if result.state == 'finished': break
