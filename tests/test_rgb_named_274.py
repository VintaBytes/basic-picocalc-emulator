"""Colores RGB(shortcut) de PicoMite 6.00.03; PCC usa LIGHTGREY."""
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import RGB_NAMED_COLORS
from basic_cde.devices.display import BitmapDisplay


@pytest.mark.parametrize('name,value', sorted(RGB_NAMED_COLORS.items()))
def test_all_rgb_shortcuts_named(name, value):
    m = BasicMachine(f'PIXEL 1,1,RGB({name.lower()})\nEND')
    result = m.step()
    assert result.graphics == ('pixel', 1, 1, value)


def test_lightgrey_pcc_no_longer_draws_black():
    m = BasicMachine('CLS RGB(lightgrey)\nPIXEL 1,1,RGB(gray)\nEND')
    d = BitmapDisplay()
    for _ in range(5):
        r = m.step()
        if r.graphics:
            d.graphics(r.graphics)
        if r.state == 'finished':
            break
    assert d.framebuffer.get_pixel(0,0)[:3] == (211,211,211)
    assert d.framebuffer.get_pixel(1,1)[:3] == (128,128,128)


def test_rgb_three_component_form_still_works():
    m = BasicMachine('PIXEL 1,1,RGB(12,34,56)\nEND')
    assert m.step().graphics == ('pixel', 1, 1, 0x0C2238)


def test_named_rgb_alias_spelling_equivalent():
    m = BasicMachine('PRINT RGB(lightgrey)=RGB(lightgray)\nPRINT RGB(grey)=RGB(gray)\nEND')
    outputs = []
    for _ in range(5):
        s=m.step()
        if s.output: outputs.append(s.output.strip())
        if s.state=='finished': break
    assert len(outputs)==2
    assert all(float(v)!=0 for v in outputs)
