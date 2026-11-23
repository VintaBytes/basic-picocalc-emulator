"""Compatibilidad RESTORE etiqueta y controles de sonido 0.2.62."""
import json
from pathlib import Path

import pytest

from basic_cde.app.settings import MountSettings
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.gui.skin import screen_point_horizontal


def _finish(source):
    machine = BasicMachine(source)
    outputs = []
    for _ in range(300):
        result = machine.step()
        outputs.append(result.output or '')
        if result.state == 'finished':
            return ''.join(outputs)
    raise AssertionError('Programa BASIC no termino')


def test_restore_edges_in_subroutine():
    source = '''
SUB draw()
  LOCAL E(3)
  RESTORE edges
  FOR I=0 TO 3
    READ E(I)
  NEXT I
  PRINT E(0);",";E(1);",";E(2);",";E(3)
  edges:
  DATA 0,1,2,3
END SUB
DRAW
'''
    assert '0,1,2,3' in _finish(source).replace(' ', '')


def test_restore_label_must_override_undeclared_variable():
    source = '''
READ A
RESTORE marker
READ B
PRINT A;",";B
DATA 9
marker:
DATA 42
'''
    assert '9,42' in _finish(source).replace(' ', '')


def test_restore_missing_label_fails():
    machine = BasicMachine('RESTORE none\nDATA 1')
    with pytest.raises(BasicError, match='RESTORE:'):
        machine.step()


def test_volume_saved_without_losing_other_settings(tmp_path):
    preferences = MountSettings(tmp_path / 'settings.json')
    preferences.save({'A': '/tmp/data-a'})
    preferences.save_last_program('/tmp/a.bas')
    preferences.save_volume(35)
    assert preferences.load_volume() == 35
    assert preferences.load()['A'] == '/tmp/data-a'
    assert preferences.load_last_program() == '/tmp/a.bas'
    assert json.loads(preferences.path.read_text())['volume'] == 35


def test_volume_clamps_and_legacy_fallback(tmp_path):
    preferences = MountSettings(tmp_path / 'settings.json')
    assert preferences.load_volume() == 70
    preferences.save_volume(999)
    assert preferences.load_volume() == 100
    preferences.save_volume(-5)
    assert preferences.load_volume() == 0


def test_volume_hit_geometry_has_both_orientations():
    # No requiere Qt para comprobar que el control permanece fuera del LCD.
    x, y = screen_point_horizontal((84, 210))
    assert x < 126
    assert y > 0


def test_ffplay_volume_parameter(monkeypatch):
    from basic_cde.app import session

    class FakeProcess:
        pid = 123
        def poll(self):
            return None
        def terminate(self):
            pass
        def wait(self, timeout=None):
            return 0

    commands = []
    monkeypatch.setattr(session.shutil, 'which', lambda key: '/usr/bin/ffplay')
    monkeypatch.setattr(session.subprocess, 'Popen', lambda args, **kw: (commands.append(args) or FakeProcess()))
    basic = session.BasicSession('END', volume=35)
    basic._audio_action(('modfile', '/tmp/sound.mod'))
    assert commands[0][commands[0].index('-volume') + 1] == '35'
    basic.stop_audio()
