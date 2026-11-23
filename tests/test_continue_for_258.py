"""Compatibilidad CONTINUE FOR para PicoCalc MMBasic 6.0003."""
import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError


def execute(source, limit=2000):
    session = BasicSession(source)
    result = []
    for _ in range(limit):
        step = session.step()
        result.append(step.output)
        if step.state == 'finished':
            return ''.join(result)
        assert step.state == 'running', step
    raise AssertionError('Programa no termina')


def test_continue_for_skips_remainder_and_increments():
    code = '''FOR I=1 TO 5
IF I=3 THEN CONTINUE FOR
PRINT I
NEXT I
PRINT "FIN"
'''
    assert execute(code).splitlines() == ['1', '2', '4', '5', 'FIN']


def test_continue_for_nested_preserves_outer_and_inner_loop():
    code = '''FOR I=1 TO 2
FOR J=1 TO 3
IF J=2 THEN CONTINUE FOR
PRINT I*10+J
NEXT J
NEXT I
'''
    assert execute(code).splitlines() == ['11', '13', '21', '23']


def test_continue_for_skips_nested_loop_not_its_next():
    code = '''FOR I=1 TO 3
CONTINUE FOR
FOR J=1 TO 2
PRINT "BAD"
NEXT J
NEXT I
PRINT "OK"
'''
    assert execute(code).strip() == 'OK'


def test_continue_for_outside_loop_errors():
    with pytest.raises(BasicError, match='CONTINUE FOR fuera de FOR'):
        execute('CONTINUE FOR\n')


def test_continue_for_from_demo_hat():
    code = '''ZP=2
FOR ZI=-4 TO 3
IF ZI<-ZP OR ZI>ZP THEN CONTINUE FOR
PRINT ZI
NEXT ZI
'''
    assert execute(code).splitlines() == ['-2', '-1', '0', '1', '2']
