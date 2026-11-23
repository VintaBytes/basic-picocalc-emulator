"""ON ERROR moderno: semántica PicoMite y compatibilidad de programas previos."""
import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def run(source):
    return BasicMachine(source).run().splitlines()


def test_skip_two_statements_and_resume_abort():
    src = '''ON ERROR SKIP 2
A=1/0
PRINT MM.ERRNO
PRINT MM.ERRNO
END'''
    assert run(src) == ['1', '1']


def test_skip_two_errors_and_preserve_last_message():
    src = '''ON ERROR SKIP 2
A=1/0
B=2/0
PRINT MM.ERRNO
PRINT MM.ERRMSG$
END'''
    result = run(src)
    assert result[0] == '1'
    assert 'linea fuente 3' in result[1]


def test_skip_expiry_does_not_swallow_third_error():
    with pytest.raises(BasicError):
        run('ON ERROR SKIP 2\nA=1/0\nB=2/0\nC=3/0')


def test_ignore_until_abort_with_clear():
    src = '''ON ERROR IGNORE
A=1/0
PRINT MM.ERRNO
ON ERROR CLEAR
PRINT MM.ERRNO
PRINT LEN(MM.ERRMSG$)
B=2/0
PRINT MM.ERRNO
ON ERROR ABORT
END'''
    assert run(src) == ['1', '0', '0', '1']


def test_abort_disables_ignore():
    with pytest.raises(BasicError):
        run('ON ERROR IGNORE\nA=1/0\nON ERROR ABORT\nB=1/0')


def test_skip_reconfiguration_at_same_count_does_not_expire():
    src = '''ON ERROR SKIP 1
ON ERROR SKIP 1
A=1/0
PRINT MM.ERRNO
END'''
    assert run(src) == ['1']


def test_skip_rejects_invalid_count():
    for arg in ('0', '-1', '1.5', '"2"'):
        with pytest.raises(BasicError):
            run(f'ON ERROR SKIP {arg}\nEND')


def test_error_state_survives_normal_instruction_after_skip():
    src = '''ON ERROR SKIP
A=1/0
B=4
PRINT MM.ERRNO
PRINT B
END'''
    assert run(src) == ['1', '4']
