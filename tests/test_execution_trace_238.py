"""La transcripción debe mostrar la ruta real, sin modificar BASIC."""
from pathlib import Path
import pytest

from basic_cde.app.trace import describe_program, run_trace
from basic_cde.app.session import BasicSession
from basic_cde.devices.drives import VirtualDrives
from basic_cde.core.expressions import BasicError


def test_trace_virtual_and_real_paths(tmp_path):
    sd = tmp_path / 'sdcard'
    program = sd / 'bas' / 'mate' / 'rpn2g.bas'
    program.parent.mkdir(parents=True)
    program.write_text('PRINT 4', encoding='utf-8')
    drives = VirtualDrives(b=sd)
    msg = run_trace('RUN inicial', program, drives)
    assert 'B:/bas/mate/rpn2g.bas' in msg
    assert str(program) in msg
    assert describe_program(None, drives) == 'memoria (sin archivo asociado)'


def test_chain_records_successful_path(tmp_path):
    sd = tmp_path / 'sd'
    folder = sd / 'bas'
    folder.mkdir(parents=True)
    file = folder / 'menu.bas'
    file.write_text('PRINT "MENU"\nEND', encoding='utf-8')
    drives = VirtualDrives(b=sd)
    session = BasicSession('RUN "B:/bas/menu.bas"', drives=drives)
    assert session.active_path is None
    session.step()
    assert session.active_path == file
    assert session.chain_requested == 'B:/bas/menu.bas'
    assert session.chain_target == file
    assert 'menu.bas' in run_trace('RUN encadenado', session.active_path, drives)
    session.step()
    assert session.chain_requested is None
    assert session.chain_target is None


def test_chain_keeps_failed_destination_for_diagnostic(tmp_path):
    sd = tmp_path / 'sd'
    folder = sd / 'bas'
    folder.mkdir(parents=True)
    file = folder / 'menu.bas'
    file.write_text('IF 1 THEN\nPRINT "BAD"', encoding='utf-8')
    drives = VirtualDrives(b=sd)
    session = BasicSession('RUN "B:/bas/menu.bas"', drives=drives)
    with pytest.raises(BasicError, match='menu.bas'):
        session.step()
    assert session.active_path is None
    assert session.chain_requested == 'B:/bas/menu.bas'
    assert session.chain_target == file


def test_gui_trace_does_not_write_on_lcd():
    from pathlib import Path
    window = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()
    assert 'self.worker.trace.connect(self.append_trace)' in window
    assert 'self.trace.emit(run_trace(' in window
    block = window.split('    def append_trace(self, value):', 1)[1].split('    def append_output(', 1)[0]
    assert 'self.transcript += value' in block
    assert 'self.display.console' not in block
    assert 'self.draw_framebuffer()' not in block
