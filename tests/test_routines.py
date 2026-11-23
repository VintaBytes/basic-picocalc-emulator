"""Pruebas de rutinas independientes de la interfaz Qt."""
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_sub_automatic_skip_and_args():
    source = '''X=5
SUMAR 4
PRINT X
END
SUB SUMAR(N)
X=X+N
END SUB'''
    assert BasicMachine(source).run() == '9\n'


def test_sub_local_shadows_global_and_restores():
    source = '''X=10
MUESTRA 7
PRINT X
END
SUB MUESTRA(N)
LOCAL X
X=N
PRINT X
END SUB'''
    assert BasicMachine(source).run() == '7\n10\n'


def test_function_result_and_local_scope():
    source = '''X=5
PRINT DOBLE(3)+1
PRINT X
END
FUNCTION DOBLE(N)
LOCAL X
X=N*2
DOBLE=X
END FUNCTION'''
    assert BasicMachine(source).run() == '7\n5\n'


def test_function_string_value():
    source = '''PRINT SALUDO$("Ana")
END
FUNCTION SALUDO$(S$)
SALUDO$="Hola "+S$
END FUNCTION'''
    assert BasicMachine(source).run() == 'Hola Ana\n'


def test_nested_sub_and_function():
    source = '''IMPRIME 4
END
SUB IMPRIME(X)
PRINT TRIPLE(X)
END SUB
FUNCTION TRIPLE(Z)
TRIPLE=Z*3
END FUNCTION'''
    assert BasicMachine(source).run() == '12\n'


def test_exit_sub_and_exit_function():
    source = '''F 1
PRINT G(2)
END
SUB F(X)
IF X THEN EXIT SUB
PRINT "MAL"
END SUB
FUNCTION G(X)
G=X+1
EXIT FUNCTION
G=0
END FUNCTION'''
    assert BasicMachine(source).run() == '3\n'


def test_mismatched_function_arguments():
    source = '''PRINT F(1,2)
END
FUNCTION F(X)
F=X
END FUNCTION'''
    with pytest.raises(BasicError, match='esperaban 1'):
        BasicMachine(source).run()


def test_local_outside_routine_fails():
    with pytest.raises(BasicError, match='LOCAL fuera'):
        BasicMachine('LOCAL X').run()


def test_routine_not_invoked_at_top_level():
    source = '''PRINT "INICIO"
SUB NUNCA()
PRINT "MAL"
END SUB
PRINT "FINAL"'''
    assert BasicMachine(source).run() == 'INICIO\nFINAL\n'


def test_lunar_original_routine_definitions_are_parsed():
    """El archivo real de la SD se facilita mediante BAS_CORPUS_ZIP."""
    import os
    from pathlib import Path
    from zipfile import ZipFile
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Definir BAS_CORPUS_ZIP con la ruta al zip original')
    with ZipFile(archive) as bundle:
        source = bundle.read('juegost/lunar_lander.bas').decode('utf-8-sig')
    machine = BasicMachine(source)
    assert 'RJUST$' in machine.routines
    assert 'LJUST$' in machine.routines
    assert machine.value('RJUST$("3",4)') == '   3'
    assert machine.value('LJUST$("3",4)') == '3   '
