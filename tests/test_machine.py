import pytest
from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine


def test_print_and_for():
    m = BasicMachine('FOR I=1 TO 3\nPRINT I\nNEXT I\nEND')
    assert m.run() == '1\n2\n3\n'


def test_for_zero_iterations():
    m = BasicMachine('FOR I=5 TO 2\nPRINT "ERROR"\nNEXT I\nPRINT "OK"')
    assert m.run() == 'OK\n'


def test_input():
    m = BasicMachine('INPUT "NOMBRE? "; A$\nPRINT "HOLA "; A$')
    assert m.run(input_provider=lambda prompt: 'ANA') == 'HOLA ANA\n'


def test_jump_numbered():
    m = BasicMachine('10 PRINT "UNO"\n20 GOTO 40\n30 PRINT "MAL"\n40 PRINT "FIN"')
    assert m.run() == 'UNO\nFIN\n'


def test_does_not_fake_support():
    with pytest.raises(BasicError, match='DEFINEFONT sin END DEFINEFONT'):
        BasicMachine('DEFINEFONT #1').run()


def test_max_steps():
    with pytest.raises(BasicError, match='Limite'):
        BasicMachine('10 GOTO 10').run(max_steps=100)
