"""PicoMite: DIM de strings con LENGTH en arrays; regression NOTAS.BAS.

La maquina real acepta DIM A$(24,12) LENGTH 32. El emulador solia
producir 'DIM no admitido' al encontrar LENGTH.
"""
import pytest
from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine


def test_notas_uses_length_on_two_arrays():
    code = """OPTION BASE 1
DIM noteText$(24,12) LENGTH 32
DIM draft$(12) LENGTH 32
noteText$(1,1)="Anotar *feriado*"
draft$(12)="Recordar sacar la basura"
PRINT noteText$(1,1)
PRINT draft$(12)
END"""
    m = BasicMachine(code)
    assert m.run() == "Anotar *feriado*\nRecordar sacar la basura\n"
    assert m.variables["NOTETEXT$"].string_length == 32
    assert m.variables["DRAFT$"].string_length == 32
    assert m.variables["NOTETEXT$"].shape == (24, 12)


def test_picomite_alternate_length_forms():
    code = """OPTION BASE 1
DIM STRING a(2,2) LENGTH 10
DIM b(2) LENGTH 5 AS STRING
DIM s$(3) LENGTH 3 = ("a","bb","ccc")
a(1,1)="Hola"
b(2)="12345"
PRINT a(1,1);":";b(2);":";s$(3)
END"""
    assert BasicMachine(code).run() == "Hola:12345:ccc\n"


@pytest.mark.parametrize("source,reason", [
    ('DIM s$(2) LENGTH 0', 'rango 1 a 255'),
    ('DIM s$(2) LENGTH 256', 'rango 1 a 255'),
    ('DIM a%(2) LENGTH 10', 'requiere STRING'),
    ('DIM a(2) LENGTH 7 AS INTEGER', 'requiere STRING'),
    ('DIM s$(2) LENGTH 2\ns$(1)="abc"', 'longitud'),
    ('DIM STRING a(2) LENGTH 3\na(1)="abcd"', 'longitud'),
    ('DIM s$(1) LENGTH 2 = ("a","abc")', 'longitud'),
])
def test_invalid_length_is_rejected(source, reason):
    with pytest.raises(BasicError, match=reason):
        BasicMachine(source + "\nEND").run()


def test_unbounded_string_arrays_still_work():
    source = """DIM s$(2)
s$(0)="Esta cadena mide mucho mas de 32 caracteres"
PRINT LEN(s$(0))
END"""
    assert BasicMachine(source).run() == "43\n"


def test_length_with_ordinary_array_declarations_same_statement():
    source = """OPTION BASE 1
DIM labels$(2) LENGTH 4, scores%(2)
labels$(1)="abcd"
scores%(2)=99
PRINT labels$(1);":";scores%(2)
END"""
    assert BasicMachine(source).run() == "abcd:99\n"
