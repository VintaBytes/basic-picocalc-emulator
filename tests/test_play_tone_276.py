"""Regresion PLAY TONE de PicoMite 6.00.03 (PicoCalc Commander)."""
from unittest.mock import patch

import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_pcc_tone_syntax_and_nonblocking_execution():
    m = BasicMachine('PLAY TONE 900,900,70\nPRINT "DIALOG"\nEND')
    first = m.step()
    assert first.state == 'running'
    assert first.audio == ('tone', 900.0, 900.0, 70.0)
    assert m.step().output == 'DIALOG\n'
    assert m.step().state == 'finished'


def test_tone_can_be_indefinite_and_uses_numeric_expressions():
    m = BasicMachine('F=440\nPLAY TONE F*2,440\nEND')
    assert m.step().state == 'running'
    assert m.step().audio == ('tone', 880.0, 440.0, None)


@pytest.mark.parametrize('source', [
    'PLAY TONE -1,900,70',
    'PLAY TONE 900,22051,70',
    'PLAY TONE 900,900,-1',
    'PLAY TONE "x",900,70',
    'PLAY TONE 900',
    'PLAY TONE 900,900,70,IRQ',
])
def test_tone_bad_args_are_not_silently_ignored(source):
    with pytest.raises(BasicError, match='PLAY TONE'):
        BasicMachine(source).step()


class FakePlayer:
    _next = 10000

    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        self.kwargs = kwargs
        self.pid = FakePlayer._next
        FakePlayer._next += 1
        self.closed = False

    def poll(self):
        return -15 if self.closed else None

    def terminate(self):
        self.closed = True

    def wait(self, timeout=1):
        return -15


def test_session_spawns_stereo_tone_no_block_and_stops_at_end(tmp_path):
    players = []

    def spawn(cmd, **kwargs):
        player = FakePlayer(cmd, **kwargs)
        players.append(player)
        return player

    session = BasicSession('PLAY TONE 900,900,70\nPRINT "OK"\nEND',
                           volume=35, persistent_path=tmp_path/'persistent.json')
    with patch('basic_cde.app.session.shutil.which', return_value='/usr/bin/ffplay'), \
         patch('basic_cde.app.session.subprocess.Popen', side_effect=spawn):
        assert session.step().state == 'running'
        assert len(players) == 1
        cmd = players[0].cmd
        assert cmd[cmd.index('-volume') + 1] == '35'
        assert cmd[cmd.index('-f') + 1] == 'lavfi'
        assert 'sin(2*PI*900*t)|sin(2*PI*900*t)' in cmd[-1]
        assert ':d=0.07' in cmd[-1]
        assert session.step().output == 'OK\n'
        assert session.step().state == 'finished'
        assert players[0].closed


def test_second_tone_replaces_first_and_play_stop_cleans(tmp_path):
    players = []

    def spawn(cmd, **kwargs):
        p = FakePlayer(cmd, **kwargs)
        players.append(p)
        return p

    session = BasicSession('PLAY TONE 440,660,50\nPLAY TONE 900,900,70\nPLAY STOP\nEND',
                           persistent_path=tmp_path/'persistent.json')
    with patch('basic_cde.app.session.shutil.which', return_value='/usr/bin/ffplay'), \
         patch('basic_cde.app.session.subprocess.Popen', side_effect=spawn):
        session.step()
        assert not players[0].closed
        session.step()
        assert players[0].closed and not players[1].closed
        session.step()
        assert players[1].closed
        assert session._mod_player is None


def test_missing_audio_backend_explicit_error(tmp_path):
    session = BasicSession('PLAY TONE 900,900,70',
                           persistent_path=tmp_path/'persistent.json')
    with patch('basic_cde.app.session.shutil.which', return_value=None):
        with pytest.raises(BasicError, match='PLAY TONE: falta ffplay'):
            session.step()


@pytest.mark.parametrize('source,expected', [
    ('PLAY TONE 0,900,70', ('tone', 0.0, 900.0, 70.0)),
    ('PLAY TONE 525,0,30', ('tone', 525.0, 0.0, 30.0)),
    ('PLAY TONE 0,0,30', ('tone', 0.0, 0.0, 30.0)),
    ('PLAY TONE 22050,22050,70', ('tone', 22050.0, 22050.0, 70.0)),
])
def test_tone_60003_zero_channels_and_22050(source, expected):
    assert BasicMachine(source).step().audio == expected


def test_tone_duration_zero_is_noop():
    first = BasicMachine('PLAY TONE 900,900,0').step()
    assert first.state == 'running'
    assert first.audio == ()
