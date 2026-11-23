"""Regresiones estructurales del protocolo COPY -> Qt -> ACK.

Estas pruebas no requieren instalar PySide6. La prueba visual se valida
separadamente en el Ubuntu con la GUI real.
"""
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / 'src/basic_cde/gui/window.py'


def test_frame_boundary_is_a_copy_to_visible_n_or_merge():
    source = SOURCE.read_text()
    assert "action == 'COPY' and len(command) >= 4" in source
    assert "str(command[3]).upper() == 'N'" in source
    assert "if action == 'MERGE':" in source


def test_graphics_flush_paces_explicit_frames_without_losing_normal_batching():
    source = SOURCE.read_text()
    assert "self.graphics.emit(('frame_batch', tuple(graphic_batch)))" in source
    assert "self.graphics.emit(('batch', tuple(graphic_batch)))" in source
    assert 'self.frame_ack.clear()' in source
    assert 'self.frame_ack.wait(timeout=0.05)' in source
    assert 'self.worker.frame_ack.set()' in source
    assert 'self.screen.repaint()' in source
    assert 'if self.stopping.is_set()' in source


def test_frame_batch_is_unpacked_as_graphic_commands():
    """No enviar el sobre frame_batch a BitmapDisplay.graphics()."""
    source = SOURCE.read_text()
    assert "graphic[0] in ('batch', 'frame_batch')" in source
    assert "commands = graphic[1] if graphic[0] == 'batch' else (graphic,)" not in source
