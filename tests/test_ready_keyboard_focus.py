"""Regresiones del enrutamiento Qt hacia la consola READY.

En CI sin Qt se verifican invariantes de codigo; en Ubuntu con PySide6
pueden activarse ademas los tests de widgets con QTest (en otra etapa).
"""
from pathlib import Path


def test_ready_has_deferred_focus_after_show():
    source = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()
    assert 'def showEvent(self, event):' in source
    assert 'QTimer.singleShot(0, self.focus_ready_input)' in source
    assert 'self.command.setFocus(Qt.FocusReason.OtherFocusReason)' in source


def test_ready_keyboard_routes_through_qlineedit_and_does_not_reinject_itself():
    source = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()
    assert 'and self.direct_ready and self.isActiveWindow()' in source
    assert 'and obj is not self.command' in source
    assert 'self.command.keyPressEvent(event)' in source
    assert 'QApplication.sendEvent(self.command, event)' not in source
    assert 'and not self._routing_ready_key' in source
    assert 'finally:' in source
    assert 'self.command.returnPressed.connect(self.submit_input)' in source
    assert 'self.command.textChanged.connect(self.preview_input)' in source


def test_running_keyboard_still_uses_mmbasic_mapping():
    source = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()
    assert 'self.worker.send_key(value)' in source
    assert 'self.input_key_gate.allow_press(' in source


def test_ready_global_filter_does_not_recursively_reinject_events():
    """El envio sincrono desde QApplication.eventFilter causaba recursión.

    El manejo por QLineEdit.keyPressEvent omite la cadena global de filtros
    y mantiene las señales de edicion, incluido Return/Enter.
    """
    source = (Path(__file__).parents[1] / 'src/basic_cde/gui/window.py').read_text()
    filter_body = source.split('    def eventFilter(', 1)[1].split('    def append_output(', 1)[0]
    assert 'QApplication.sendEvent(' not in filter_body
    assert 'self.command.keyPressEvent(event)' in filter_body
    assert 'self._routing_ready_key = True' in filter_body
    assert 'self._routing_ready_key = False' in filter_body
