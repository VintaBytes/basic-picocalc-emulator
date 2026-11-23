"""Regresiones PicoCalc 6.0003: EXIT FOR y PLAY MODFILE."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives


def execute(source, *, drives=None, limit=2000):
    session = BasicSession(source, drives=drives)
    output = []
    for _ in range(limit):
        r = session.step()
        output.append(r.output)
        if r.state == 'finished':
            return ''.join(output)
        assert r.state == 'running', r
    raise AssertionError('Ejecucion sin finalizar')


def test_exit_for_simple():
    code = '''FOR I=1 TO 8
PRINT I
IF I=3 THEN EXIT FOR
NEXT I
PRINT "FIN"
'''
    assert execute(code).splitlines() == ['1', '2', '3', 'FIN']


def test_exit_for_nested_does_not_abandon_outer_for():
    code = '''FOR I=1 TO 2
FOR J=1 TO 5
PRINT I*10+J
EXIT FOR
NEXT J
NEXT I
'''
    assert execute(code).splitlines() == ['11', '21']


def test_exit_for_with_nested_loop_in_skipped_remainder():
    code = '''FOR I=1 TO 2
EXIT FOR
FOR J=1 TO 3
PRINT "ERROR"
NEXT J
NEXT I
PRINT "OK"
'''
    assert execute(code).strip() == 'OK'


def test_exit_for_without_for_errors():
    with pytest.raises(BasicError, match='EXIT FOR fuera de FOR'):
        execute('EXIT FOR\n')


def test_play_modfile_resolves_virtual_drive_and_stops(tmp_path):
    sound = tmp_path / 'laamaa.mod'
    sound.write_bytes(b'MOD dummy file')
    drives = VirtualDrives(a=tmp_path)
    fake_process = MagicMock()
    fake_process.poll.return_value = None
    fake_process.wait.return_value = 0
    with patch('basic_cde.app.session.shutil.which', return_value='/usr/bin/ffplay'), \
         patch('basic_cde.app.session.subprocess.Popen', return_value=fake_process) as popen:
        execute('PLAY MODFILE "laamaa.mod"\nPLAY STOP\n', drives=drives)
    argv = popen.call_args.args[0]
    assert argv[0] == '/usr/bin/ffplay'
    assert argv[-1] == str(sound)
    fake_process.terminate.assert_called_once()


def test_play_modfile_missing_file_is_explicit(tmp_path):
    with pytest.raises(BasicError, match='archivo no encontrado'):
        execute('PLAY MODFILE "missing.mod"', drives=VirtualDrives(a=tmp_path))


def test_play_modfile_missing_ffplay_is_explicit(tmp_path):
    (tmp_path / 'test.mod').write_bytes(b'fixture')
    with patch('basic_cde.app.session.shutil.which', return_value=None):
        with pytest.raises(BasicError, match='falta ffplay'):
            execute('PLAY MODFILE "test.mod"', drives=VirtualDrives(a=tmp_path))
