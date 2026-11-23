"""Regresiones: dragon original y reduccion de señales de dibujo Qt."""
from pathlib import Path
import os
import zipfile

from basic_cde.app.session import BasicSession
from basic_cde.core.machine import BasicMachine
from basic_cde.devices.framebuffer import Framebuffer


def test_local_initializer_in_sub_evaluates_with_caller_context():
    source = '''
    X=10
    MOVE 2
    PRINT X
    END
    SUB MOVE(D)
      LOCAL X=X+D, Y=3
      PRINT X, Y
    END SUB
    '''
    machine = BasicMachine(source)
    output = machine.run(max_steps=200)
    assert '12' in output
    assert '3' in output
    assert output.rstrip().endswith('10')


def test_local_string_initializer_preserves_literal_case():
    source = '''
    SAY
    END
    SUB SAY
      LOCAL S$="MiXeD"
      PRINT S$
    END SUB
    '''
    assert 'MiXeD' in BasicMachine(source).run(max_steps=100)


def test_increment_decrement_commands():
    source = '''
    X=10
    INC X,3
    DEC X
    PRINT X
    END
    '''
    assert '12' in BasicMachine(source).run(max_steps=100)


def test_framebuffer_pixel_fast_path_preserves_rgba_and_clipping():
    fb = Framebuffer(3, 2)
    fb.pixel(1, 1, 16, 34, 80)
    fb.pixel(-1, 1, 255, 255, 255)
    fb.pixel(3, 1, 255, 255, 255)
    assert fb.get_pixel(1, 1) == (16, 34, 80, 255)
    assert fb.get_pixel(0, 1) == (0, 0, 0, 255)


def test_dragon_from_original_sd_proceeds_past_local_and_inc():
    corpus = os.environ.get('BAS_CORPUS_ZIP')
    if not corpus or not Path(corpus).is_file():
        import pytest
        pytest.skip('BAS_CORPUS_ZIP no disponible')
    with zipfile.ZipFile(corpus) as archive:
        source = archive.read('graficos/dragon.bas').decode('latin1')
    session = BasicSession(source)
    input_count = 0
    drawing_count = 0
    for i in range(12000):
        step = session.step()
        drawing_count += bool(step.graphics and step.graphics[0] in ('line','text','cls'))
        if step.state == 'waiting_input':
            input_count += 1
            if input_count == 1:
                session.input_value('5')
            else:
                break
    assert input_count == 2
    assert drawing_count > 10


def test_gui_batches_graphics_and_does_not_reinject_keyboard_events():
    module = Path(__file__).resolve().parents[1] / 'src/basic_cde/gui/window.py'
    source = module.read_text()
    assert "self.graphics.emit(('batch', tuple(graphic_batch)))" in source
    assert "len(graphic_batch) >= 512" in source
    assert 'for command in commands:' in source
    # La ruta de teclado stabilizada en la version 0.2.27 no se cambia.
    assert 'QApplication.sendEvent(self.command, event)' not in source
