"""Regresiones extraidas de demo.bas y audio con ffplay."""
import json
from unittest.mock import patch

from basic_cde.app.session import BasicSession
from basic_cde.app.audio_volume import _sink_for_pid, set_player_volume


def run(source):
    session = BasicSession(source)
    output = []
    for _ in range(200):
        result = session.step()
        output.append(result.output)
        if result.state == 'finished':
            return ''.join(output)
        assert result.state == 'running', result
    raise AssertionError('No termino')


def test_demo_ball_step_without_space():
    assert run('FOR d=6 TO 1step -1\nPRINT d\nNEXT d\n').splitlines() == [
        '6', '5', '4', '3', '2', '1'
    ]


def test_for_step_with_spaces_unchanged():
    assert run('FOR d=6 TO 1 STEP -2\nPRINT d\nNEXT d\n').splitlines() == ['6', '4', '2']


def test_for_without_step_and_variable_named_stepvalue():
    assert run('STEPVALUE=3\nFOR d=1 TO STEPVALUE\nPRINT d\nNEXT\n').splitlines() == ['1','2','3']


def test_detects_pactl_json_own_stream_only():
    s = json.dumps([{'index': 42, 'properties': {'application.process.id': '900'}},
                    {'index': 43, 'properties': {'application.process.id': '901'}}])
    assert _sink_for_pid(s, 901) == '43'
    assert _sink_for_pid(s, 902) is None


def test_detects_pactl_text_own_stream_only():
    s = 'Sink Input #24\n  application.process.id = "900"\nSink Input #29\n  application.process.id = "901"\n'
    assert _sink_for_pid(s, 901) == '29'


def test_pactl_volume_change_targets_only_match():
    output = json.dumps([{'index': 42, 'properties': {'application.process.id': '900'}}])
    from subprocess import CompletedProcess
    with patch('basic_cde.app.audio_volume.shutil.which', return_value='/usr/bin/pactl'), \
         patch('basic_cde.app.audio_volume.subprocess.run', side_effect=[
             CompletedProcess([],0,stdout=output), CompletedProcess([],0,stdout='')]) as proc:
        assert set_player_volume(900, 35)
        assert proc.call_args_list[-1].args[0] == [
            'pactl','set-sink-input-volume','42','35%']
