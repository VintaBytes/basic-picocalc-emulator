"""ASC con cadena vacia: comportamiento comprobado en Functions.c / fun_asc."""
import pytest

from basic_cde.core.expressions import BasicError, evaluate
from basic_cde.core.machine import BasicMachine


@pytest.mark.parametrize(('expression', 'expected'), [
    ('ASC("")', 0),
    ('ASC("A")', 65),
    ('ASC(CHR$(13))', 13),
    ('ASC("AB")', 65),
])
def test_asc_firmware_60003(expression, expected):
    assert evaluate(expression) == expected


def test_asc_rejects_non_string():
    with pytest.raises(BasicError, match='ASC'):
        evaluate('ASC(123)')


def test_picofile_inkey_empty_no_python_exception():
    # Guardar INKEY$ vacia y llamar ASC sobre ella es valido en MMBasic:
    # el firmware devuelve 0, no IndexError.
    machine = BasicMachine('key$=""\nk=ASC(key$)\nPRINT k\nEND')
    results = [machine.step() for _ in range(4)]
    assert results[2].output.strip() == '0'
    assert machine.variables['K'] == 0
