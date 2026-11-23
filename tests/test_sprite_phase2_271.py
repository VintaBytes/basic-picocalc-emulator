"""SPRITE SHOW/HIDE/SHOW SAFE/HIDE SAFE/SWAP (manual 6.00.03)."""
import pytest
from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError


def run(source):
    session = BasicSession(source)
    for i in range(150):
        event=session.step()
        if event.state == 'finished':
            return session
    pytest.fail('no termino')


def at(s,x,y):
    return s.display.framebuffer.get_pixel(x,y)[:3]


def test_show_hide_restores_exact_background():
    s=run('''CLS RGB(10,20,30)
BOX 10,10,4,4,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,10,10,4,4
CLS RGB(10,20,30)
SPRITE SHOW #1,80,80,0
SPRITE HIDE #1
END''')
    assert at(s,80,80) == (10,20,30)
    assert 1 in s.display.sprite_buffers
    assert s.display.sprite_visible == {}


def test_show_move_no_trails():
    s=run('''CLS RGB(10,20,30)
BOX 10,10,4,4,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,10,10,4,4
CLS RGB(10,20,30)
SPRITE SHOW #1,20,20,0
SPRITE SHOW #1,30,30,0
END''')
    assert at(s,20,20) == (10,20,30)
    assert at(s,30,30) == (255,0,0)


def test_hide_safe_retains_above_sprite():
    s=run('''CLS RGB(5,10,15)
BOX 0,0,6,6,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,0,0,6,6
CLS RGB(5,10,15)
BOX 0,0,6,6,,RGB(0,255,0),RGB(0,255,0)
SPRITE READ #2,0,0,6,6
CLS RGB(5,10,15)
SPRITE SHOW #1,40,40,0
SPRITE SHOW #2,43,43,0
SPRITE HIDE SAFE #1
END''')
    assert at(s,40,40)==(5,10,15)
    assert at(s,43,43)==(0,255,0)
    assert at(s,48,48)==(0,255,0)
    assert s.display.sprite_order == [2]
    # El fondo del sprite 2 se re-captura limpio; al ocultarlo no deja residuos.
    s.display.sprite_command('HIDE',2)
    assert at(s,43,43)==(5,10,15)


def test_show_safe_preserves_z_order():
    s=run('''CLS
BOX 0,0,6,6,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,0,0,6,6
BOX 0,0,6,6,,RGB(0,255,0),RGB(0,255,0)
SPRITE READ #2,0,0,6,6
CLS RGB(5,10,15)
SPRITE SHOW #1,40,40,0
SPRITE SHOW #2,43,43,0
SPRITE SHOW SAFE #1,42,42,0
END''')
    assert at(s,43,43)==(0,255,0)
    assert at(s,42,42)==(255,0,0)
    assert at(s,40,40)==(5,10,15)
    assert s.display.sprite_order==[1,2]


def test_show_safe_ontop_and_swap():
    s=run('''CLS
BOX 0,0,6,6,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,0,0,6,6
BOX 0,0,6,6,,RGB(0,255,0),RGB(0,255,0)
SPRITE READ #2,0,0,6,6
BOX 0,0,6,6,,RGB(0,0,255),RGB(0,0,255)
SPRITE READ #3,0,0,6,6
CLS RGB(5,10,15)
SPRITE SHOW #1,40,40,0
SPRITE SHOW #2,43,43,0
SPRITE SHOW SAFE #1,42,42,0,0,1
SPRITE SWAP #1,#3
END''')
    assert at(s,43,43)==(0,0,255)
    assert at(s,42,42)==(0,0,255)
    assert at(s,40,40)==(5,10,15)
    assert s.display.sprite_order==[2,3]
    s.display.sprite_command('HIDE',3)
    assert at(s,43,43)==(0,255,0)


def test_swap_keeps_background_and_position():
    s=run('''CLS
BOX 0,0,3,3,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,0,0,3,3
BOX 0,0,3,3,,RGB(0,255,0),RGB(0,255,0)
SPRITE READ #2,0,0,3,3
CLS RGB(10,20,30)
SPRITE SHOW #1,50,60,0
SPRITE SWAP #1,#2
END''')
    assert at(s,50,60) == (0,255,0)
    assert 2 in s.display.sprite_visible and 1 not in s.display.sprite_visible
    s.display.sprite_command('HIDE',2)
    assert at(s,50,60)==(10,20,30)


def test_show_clip_and_orientation():
    s=run('''CLS
PIXEL 0,0,RGB(255,0,0)
PIXEL 1,0,RGB(0,0,255)
SPRITE READ #1,0,0,2,1
CLS RGB(20,20,20)
SPRITE SHOW #1,319,20,0,1
END''')
    assert at(s,319,20)==(0,0,255)


@pytest.mark.parametrize('source',[
    'SPRITE SHOW #1,0,0,0',
    'SPRITE HIDE #1',
    'SPRITE HIDE SAFE #1',
    'SPRITE SWAP #1,#2',
    'SPRITE SHOW #1,0,0,0,8',
    'SPRITE SHOW SAFE #1,0,0,0,0,2',
    'SPRITE SHOW #1,0,0,0,0,1',
])
def test_invalid_phase2(source):
    s=BasicSession(source)
    with pytest.raises(BasicError):
        for _ in range(12):
            s.step()


def test_close_visible_does_not_erase_screen():
    s=run('''CLS
BOX 0,0,3,3,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,0,0,3,3
CLS RGB(12,12,12)
SPRITE SHOW #1,80,90,0
SPRITE CLOSE #1
END''')
    assert at(s,80,90)==(255,0,0)
    assert not s.display.sprite_visible
    assert not s.display.sprite_buffers


def test_show_and_hide_on_auxiliary_framebuffer():
    s=run('''FRAMEBUFFER CREATE
FRAMEBUFFER WRITE F
CLS
BOX 0,0,3,3,,RGB(255,0,0),RGB(255,0,0)
SPRITE READ #1,0,0,3,3
CLS RGB(12,12,12)
SPRITE SHOW #1,80,90,0
FRAMEBUFFER COPY F,N
SPRITE HIDE #1
END''')
    assert at(s,80,90)==(255,0,0)
    assert s.display.buffers['F'].get_pixel(80,90)[:3]==(12,12,12)
