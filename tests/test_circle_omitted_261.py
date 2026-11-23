"""Regression for CIRCLE calls in the unmodified disco() routine."""
import pytest
from basic_cde.app.session import BasicSession
from basic_cde.devices.display import BitmapDisplay
from basic_cde.core.expressions import BasicError


def _run(code):
    session = BasicSession(code)
    for _ in range(50):
        result = session.step()
        if result.state == 'finished':
            break
    else:
        pytest.fail('Program did not finish')
    return session.display


def test_circle_omitted_width_and_aspect_filled():
    d = _run('''
    CLS 0
    CIRCLE 20,20,4,,,RGB(200,100,150),RGB(200,100,150)
    ''')
    assert d.framebuffer.get_pixel(20, 20)[:3] == (200,100,150)


def test_circle_omitted_width_and_aspect_unfilled():
    d = _run('''
    CLS 0
    CIRCLE 20,20,4,,,RGB(255,0,0)
    ''')
    assert d.framebuffer.get_pixel(20,20)[:3] == (0,0,0)
    assert d.framebuffer.get_pixel(24,20)[:3] == (255,0,0)


def test_circle_negative_one_fill_is_transparent():
    d = _run('''
    CLS 0
    CIRCLE 20,20,4,1,1,RGB(255,0,0),-1
    ''')
    assert d.framebuffer.get_pixel(20,20)[:3] == (0,0,0)


def test_explicit_zero_aspect_still_invalid():
    d = BitmapDisplay(40,40)
    with pytest.raises(BasicError, match='aspecto cero'):
        d.circle(20,20,4,1,0,0)
