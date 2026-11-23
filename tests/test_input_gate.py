"""Regresiones del cambio entre LINE INPUT y lectura INKEY$."""

from basic_cde.gui.input_gate import InputKeyGate


def test_enter_used_for_line_input_must_not_reach_inkey():
    gate = InputKeyGate()
    gate.after_input()
    assert not gate.allow_press(enter=True)
    assert not gate.allow_press(enter=True, auto_repeat=True)
    gate.release(enter=True)
    assert gate.allow_press(enter=False)
    assert gate.allow_press(enter=True)


def test_release_of_other_key_does_not_allow_stale_enter():
    gate = InputKeyGate()
    gate.after_input()
    gate.release(enter=False)
    assert not gate.allow_press(enter=True)
    gate.reset()
    assert gate.allow_press(enter=True)


def test_new_letter_can_be_first_intentional_input_even_if_release_lost():
    gate = InputKeyGate()
    gate.after_input()
    assert not gate.allow_press(enter=False, auto_repeat=True)
    assert gate.allow_press(enter=False, auto_repeat=False)
    assert gate.allow_press(enter=True)
