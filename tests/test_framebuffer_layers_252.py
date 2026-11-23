"""N/F/L virtuales, sin depender de Qt ni del dispositivo fisico."""
import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay
from basic_cde.app.direct import DirectConsole


def run_bas(source):
    session = BasicSession(source)
    for _ in range(200):
        step = session.step()
        if step.state in ('finished', 'error'):
            return session
    raise AssertionError('Programa sin terminar')


def test_offscreen_drawing_is_invisible_until_copy():
    d = BitmapDisplay()
    d.graphics(('framebuffer', 'CREATE'))
    d.graphics(('framebuffer', 'WRITE', 'F'))
    d.graphics(('pixel', 12, 14, 0xFFAA22))
    assert d.framebuffer.get_pixel(12, 14)[:3] == (0, 0, 0)
    assert d.buffers['F'].get_pixel(12, 14)[:3] == (255, 170, 34)
    d.graphics(('framebuffer', 'COPY', 'F', 'N'))
    assert d.framebuffer.get_pixel(12, 14)[:3] == (255, 170, 34)


def test_layer_merge_preserves_offscreen_planes():
    d = BitmapDisplay(8, 8)
    d.graphics(('framebuffer', 'CREATE'))
    d.graphics(('framebuffer', 'LAYER'))
    d.graphics(('framebuffer', 'WRITE', 'F'))
    d.graphics(('cls', 0x111122))
    d.graphics(('framebuffer', 'WRITE', 'L'))
    d.graphics(('cls', 0))
    d.graphics(('pixel', 3, 4, 0xFF0000))
    before_f = d.buffers['F'].snapshot()
    before_l = d.buffers['L'].snapshot()
    d.graphics(('framebuffer', 'MERGE', 0))
    assert d.framebuffer.get_pixel(0, 0)[:3] == (17, 17, 34)
    assert d.framebuffer.get_pixel(3, 4)[:3] == (255, 0, 0)
    assert d.buffers['F'].snapshot() == before_f
    assert d.buffers['L'].snapshot() == before_l


def test_close_returns_target_to_visible_n():
    d = BitmapDisplay()
    d.graphics(('framebuffer', 'CREATE'))
    d.graphics(('framebuffer', 'WRITE', 'F'))
    d.graphics(('framebuffer', 'CLOSE', 'F'))
    assert d.write_target == 'N'
    assert set(d.buffers) == {'N'}
    d.graphics(('pixel', 0, 0, 0x00FF00))
    assert d.framebuffer.get_pixel(0, 0)[:3] == (0, 255, 0)


def test_missing_target_reports_error_not_implicit_allocation():
    d = BitmapDisplay()
    with pytest.raises(BasicError, match='Invalid framebuffer'):
        d.graphics(('framebuffer', 'WRITE', 'F'))
    with pytest.raises(BasicError, match='Invalid framebuffer'):
        d.graphics(('framebuffer', 'COPY', 'F', 'N'))


def test_bas_program_routes_drawing_and_text_to_auxiliary_frame():
    source = '''FRAMEBUFFER CREATE
FRAMEBUFFER WRITE F
CLS RGB(0,0,0)
PIXEL 0,0,RGB(255,0,0)
TEXT 15,20,"HELLO"
FRAMEBUFFER COPY F,N
END'''
    session = run_bas(source)
    d = session.display
    assert d.framebuffer.get_pixel(0, 0)[:3] == (255, 0, 0)
    assert d.framebuffer.get_pixel(15, 20)[:3] != (255, 0, 0)
    assert d.write_target == 'F'


def test_direct_ready_recognizes_framebuffer():
    result = DirectConsole().execute('FRAMEBUFFER CREATE')
    assert result.action == 'immediate'
    assert result.argument == 'FRAMEBUFFER CREATE'
