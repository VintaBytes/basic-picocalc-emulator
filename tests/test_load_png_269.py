"""LOAD PNG en WebMite RP2350A: carga, paleta y transparencia."""
import pytest
from PIL import Image
from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives


def execute(source, drives):
    session = BasicSession(source, drives=drives)
    for _ in range(30):
        result = session.step()
        if result.state == 'finished':
            break
    else:
        pytest.fail('No termino el programa')
    return session.display.framebuffer


def image_file(tmp_path):
    im = Image.new('RGBA', (4, 2), (100, 150, 200, 255))
    im.putpixel((0, 0), (255, 12, 24, 0))
    im.putpixel((1, 0), (255, 12, 24, 19))
    im.putpixel((2, 0), (255, 12, 24, 20))
    im.save(tmp_path / 'imagen.png')


def test_png_basic_without_extension_and_coordinates(tmp_path):
    image_file(tmp_path)
    fb = execute('CLS 0\nLOAD PNG "imagen",20,21\nEND', VirtualDrives(a=tmp_path))
    assert fb.get_pixel(22, 21)[:3] == (255, 12, 24)
    assert fb.get_pixel(20, 21)[:3] == (0, 0, 0)
    assert fb.get_pixel(23, 21)[:3] == (100, 150, 200)


def test_png_transparent_minus_one_preserves_background(tmp_path):
    image_file(tmp_path)
    fb = execute('CLS RGB(23,45,67)\nLOAD PNG "imagen.png",10,10,-1,20\nEND', VirtualDrives(a=tmp_path))
    assert fb.get_pixel(10, 10)[:3] == (23, 45, 67)
    assert fb.get_pixel(11, 10)[:3] == (23, 45, 67)
    assert fb.get_pixel(12, 10)[:3] == (255, 12, 24)


def test_png_transparent_palette_rgb121(tmp_path):
    image_file(tmp_path)
    fb = execute('LOAD PNG "imagen",1,1,11,20\nEND', VirtualDrives(a=tmp_path))
    assert fb.get_pixel(1, 1)[:3] == (255, 85, 255)
    assert fb.get_pixel(2, 1)[:3] == (255, 85, 255)
    assert fb.get_pixel(3, 1)[:3] == (255, 12, 24)


def test_png_writes_auxiliary_framebuffer(tmp_path):
    image_file(tmp_path)
    fb = execute('FRAMEBUFFER CREATE\nFRAMEBUFFER WRITE F\nLOAD PNG "imagen",317,319\nFRAMEBUFFER COPY F,N\nEND', VirtualDrives(a=tmp_path))
    assert fb.get_pixel(319,319)[:3] == (255,12,24)
    # El pixel opaco x+2 sobrevive a la copia F -> N.
    assert fb.get_pixel(0,0)[:3] == (0,0,0)


@pytest.mark.parametrize('source', [
    'LOAD PNG "x",0,0,16',
    'LOAD PNG "x",0,0,-2',
    'LOAD PNG "x",0,0,-1,256',
    'LOAD PNG "x",0,0,0,-1',
    'LOAD PNG "x",0,0,0,20,1',
])
def test_png_invalid_arguments(source, tmp_path):
    session = BasicSession(source, drives=VirtualDrives(a=tmp_path))
    with pytest.raises(BasicError):
        session.step()


def test_png_rejects_wrong_image_format(tmp_path):
    Image.new('RGB', (2, 2), 'red').save(tmp_path/'wrong.png', format='JPEG')
    session = BasicSession('LOAD PNG "wrong.png"',drives=VirtualDrives(a=tmp_path))
    with pytest.raises(BasicError, match='formato PNG'):
        session.step()
