"""Regresion LOAD JPG/IMAGE: sin PySide6 y sobre unidades A:/B:."""
from io import BytesIO
import pytest
from PIL import Image

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives
from basic_cde.devices.display import BitmapDisplay


def run(source, drives=None):
    session = BasicSession(source, drives=drives)
    steps = []
    for _ in range(60):
        result = session.step()
        steps.append(result)
        if result.state == 'finished':
            return session, steps
    pytest.fail('No finalizo')


def test_load_jpg_with_coordinates(tmp_path):
    image = Image.new('RGB',(4,3),'red')
    image.save(tmp_path/'photo.jpg', quality=100, subsampling=0)
    drives=VirtualDrives(a=tmp_path)
    source='CLS 0\nLOAD JPG "photo.jpg",10,20\nEND'
    session,steps=run(source, drives)
    pixel=session.display.framebuffer.get_pixel(10,20)
    assert pixel[0]>=240 and pixel[1]<15
    assert session.display.framebuffer.get_pixel(9,20)==(0,0,0,255)
    assert any(s.graphics and s.graphics[0]=='load_raster' for s in steps)


def test_jpg_clips_at_display_bounds_and_draws_in_f(tmp_path):
    Image.new('RGB',(6,6),(40,100,180)).save(tmp_path/'small.jpg')
    source='FRAMEBUFFER CREATE\nFRAMEBUFFER WRITE F\nLOAD JPG "small.jpg",318,319\nFRAMEBUFFER COPY F,N\nEND'
    session,_=run(source,VirtualDrives(a=tmp_path))
    assert all(abs(actual - expected) <= 2 for actual, expected in zip(session.display.framebuffer.get_pixel(319,319)[:3], (40,100,180)))
    assert session.display.framebuffer.get_pixel(0,0)[:3] == (0,0,0)


def test_load_bmp_without_extension(tmp_path):
    Image.new('RGB',(3,3),(0,200,33)).save(tmp_path/'pic.bmp')
    session,_=run('LOAD IMAGE "pic"\nEND',VirtualDrives(a=tmp_path))
    assert session.display.framebuffer.get_pixel(0,0)[:3]==(0,200,33)


def test_progressive_rejected(tmp_path):
    Image.new('RGB',(12,12),(100,20,30)).save(tmp_path/'progressive.jpg',progressive=True)
    s=BasicSession('LOAD JPG "progressive.jpg"\nEND',drives=VirtualDrives(a=tmp_path))
    with pytest.raises(BasicError,match='progresivo'):
        s.step()


def test_missing_or_escape_rejected(tmp_path):
    for name in ('../secret.jpg','missing.jpg'):
        s=BasicSession(f'LOAD JPG "{name}"',drives=VirtualDrives(a=tmp_path))
        with pytest.raises(BasicError):s.step()


def test_direct_parser_rejects_wrong_args():
    for source in ('LOAD JPG "photo.jpg",1,2,3','LOAD JPG "photo.jpg",','LOAD IMAGE ""'):
        s=BasicSession(source)
        with pytest.raises(BasicError):s.step()


def test_load_jpg_adjacent_to_chained_bas(tmp_path):
    (tmp_path/'graficos').mkdir()
    Image.new('RGB',(2,2),(33,77,111)).save(tmp_path/'graficos'/'ariel.jpg')
    (tmp_path/'graficos'/'imgariel.bas').write_text('LOAD JPG "ariel.jpg"\nEND')
    drives=VirtualDrives(a=tmp_path)
    session=BasicSession('RUN "A:/graficos/imgariel.bas"',drives=drives)
    for _ in range(10):
        step=session.step()
        if step.state=='finished':break
    assert all(abs(actual - expected) <= 2 for actual, expected in zip(session.display.framebuffer.get_pixel(0,0)[:3], (33,77,111)))
