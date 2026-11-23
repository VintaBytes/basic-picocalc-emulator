"""Casos graficos de demo.bas; no modificar el BAS del usuario."""
from basic_cde.app.session import BasicSession
from basic_cde.devices.display import BitmapDisplay


def test_box_no_positive_area_does_not_draw_or_raise():
    disp = BitmapDisplay(32, 32)
    before = disp.framebuffer.snapshot()
    disp.box(3, -20, 9, -4, color=0xffffff)
    disp.box(3, 3, 0, 6, color=0xffffff)
    disp.box(3, 3, 9, 0, color=0xffffff)
    assert disp.framebuffer.snapshot() == before


def test_box_clips_positive_area_extending_above_screen():
    disp = BitmapDisplay(32, 32)
    disp.box(3, -3, 8, 10, thickness=0, fill=0xff0000)
    assert disp.framebuffer.get_pixel(3, 0)[:3] == (255, 0, 0)
    assert disp.framebuffer.get_pixel(10, 6)[:3] == (255, 0, 0)
    assert disp.framebuffer.get_pixel(10, 7)[:3] == (0, 0, 0)


def test_matrix_box_expression_from_unmodified_demo():
    source = '''
    FH=8:X=0:Y0=-100:FW=8
    BOX X,Y0-4*FH,X+FW-1,Y0-3*FH-1,,0
    PRINT "CONTINUA"
    '''
    session = BasicSession(source)
    output = []
    for _ in range(20):
        res = session.step()
        output.append(res.output or '')
        if res.state == 'finished':
            break
    assert 'CONTINUA' in ''.join(output)
