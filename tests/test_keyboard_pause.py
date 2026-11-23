"""Regresiones de entrada por teclas y pausas no bloqueantes."""

import pytest

from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine, KeyboardBuffer


def test_empty_inkey_is_immediate_and_nonblocking():
    machine = BasicMachine('PRINT LEN(INKEY$)\nEND')
    assert machine.run() == '0\n'


def test_key_fifo_and_parenthesized_inkey():
    keyboard = KeyboardBuffer()
    keyboard.push('ab')
    machine = BasicMachine('PRINT INKEY$; INKEY$(); INKEY$\nEND', keyboard=keyboard)
    assert machine.run() == 'ab\n'


def test_key_before_waiting_loop():
    keyboard = KeyboardBuffer()
    machine = BasicMachine('DO\nK$=INKEY$\nLOOP UNTIL K$<>""\nPRINT K$', keyboard=keyboard)
    for _ in range(15):
        assert machine.step().state == 'running'
    keyboard.push('Z')
    assert machine.run() == 'Z\n'


def test_pause_uses_injected_clock_in_milliseconds():
    now = [10.0]
    machine = BasicMachine('PRINT "A"\nPAUSE 250\nPRINT "B"\nEND', clock=lambda: now[0])
    assert machine.step().output == 'A\n'
    assert machine.step().state == 'waiting_time'
    assert machine.step().state == 'waiting_time'
    now[0] = 10.249
    assert machine.step().state == 'waiting_time'
    now[0] = 10.250
    assert machine.step().output == 'B\n'
    assert machine.step().state == 'finished'


def test_pause_zero_continues():
    assert BasicMachine('PAUSE 0\nPRINT "OK"').run() == 'OK\n'


def test_pause_rejects_negative_and_invalid_values():
    with pytest.raises(BasicError, match='PAUSE requiere'):
        BasicMachine('PAUSE -1').run()
    with pytest.raises(BasicError, match='INKEY\\$: no acepta'):
        BasicMachine('PRINT INKEY$(4)').run()


def test_keyboard_preserves_control_characters():
    keyboard = KeyboardBuffer()
    keyboard.push('\r\x08\x1b')
    assert [keyboard.read() for _ in range(4)] == ['\r', '\x08', '\x1b', '']


def test_pause_without_busy_wait_in_step():
    machine = BasicMachine('PAUSE 10000\nPRINT "NO"')
    assert machine.step().state == 'waiting_time'
    for _ in range(1000):
        assert machine.step().state == 'waiting_time'
    assert machine.instructions == 1
