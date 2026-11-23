"""Codigos documentados en Appendix H, PicoMite 6.00.01 rev. 5."""
import pytest
Qt = pytest.importorskip("PySide6.QtCore").Qt
from basic_cde.gui.keymap import mmbasic_key
from basic_cde.core.machine import KeyboardBuffer, BasicMachine

K = Qt.Key
M = Qt.KeyboardModifier


def test_arrows_and_navigation():
    expected = [(K.Key_Up,128),(K.Key_Down,129),(K.Key_Left,130),
                (K.Key_Right,131),(K.Key_Insert,132),(K.Key_Home,134),
                (K.Key_End,135),(K.Key_PageUp,136),(K.Key_PageDown,137),
                (K.Key_Delete,127),(K.Key_Print,157),(K.Key_Pause,158)]
    for key, code in expected:
        assert ord(mmbasic_key(key)) == code


def test_function_keys_normal_and_shift():
    for index in range(12):
        key = K(int(K.Key_F1) + index)
        assert ord(mmbasic_key(key)) == 145 + index
        assert ord(mmbasic_key(key, M.ShiftModifier)) == 209 + index


def test_modified_navigation_and_modifiers():
    for key, code in [(K.Key_Tab,159),(K.Key_Delete,160),
                      (K.Key_Down,161),(K.Key_Right,163)]:
        assert ord(mmbasic_key(key,M.ShiftModifier)) == code
    assert ord(mmbasic_key(K.Key_Alt)) == 139
    assert mmbasic_key(K.Key_Shift) == ''
    assert mmbasic_key(K.Key_Control) == ''
    assert mmbasic_key(K.Key_Alt,auto_repeat=True) == ''
    assert mmbasic_key(K.Key_Left,M.ControlModifier) == ''


def test_control_ascii_and_normal_keys():
    assert mmbasic_key(K.Key_A,M.ControlModifier) == chr(1)
    assert mmbasic_key(K.Key_Z,M.ControlModifier) == chr(26)
    assert mmbasic_key(K.Key_Space,M.NoModifier,' ') == ' '
    assert mmbasic_key(K.Key_Return) == '\r'
    assert mmbasic_key(K.Key_Backspace) == '\x08'
    assert mmbasic_key(K.Key_Escape) == '\x1b'
    assert mmbasic_key(K.Key_X,M.NoModifier,'x') == 'x'
    assert mmbasic_key(K.Key_X,M.AltModifier,'x') == ''


def test_nonascii_inkey_reaches_basic_as_single_character():
    kb = KeyboardBuffer()
    kb.push(mmbasic_key(K.Key_Up))
    kb.push(mmbasic_key(K.Key_F12))
    assert BasicMachine('PRINT ASC(INKEY$)\nPRINT ASC(INKEY$)\nEND',keyboard=kb).run() == '128\n156\n'
