"""Pruebas de arreglos de una dimensión y argumentos de array MMBasic."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine


def test_array_integer_string_and_option_base_one():
    source = '''OPTION BASE 1
N%=2
DIM ATAJOS%(N%)
DIM TEXTOS$(N%)
ATAJOS%(1)=65
TEXTOS$(2)="PicoCalc"
PRINT ATAJOS%(1);":";TEXTOS$(2)
END'''
    assert BasicMachine(source).run() == '65:PicoCalc\n'


def test_array_by_reference_in_function():
    source = '''OPTION BASE 1
DIM ATAJOS%(2)
ATAJOS%(1)=65
PRINT ELEGIR%(ATAJOS%())
PRINT ATAJOS%(1)
END
FUNCTION ELEGIR%(A%())
A%(1)=A%(1)+1
ELEGIR%=A%(1)
END FUNCTION'''
    assert BasicMachine(source).run() == '66\n66\n'


def test_array_parameters_multiple_types():
    source = '''DIM A%(3)
DIM B$(3)
A%(0)=7
B$(0)="ok"
PRINT F%(A%(),B$())
END
FUNCTION F%(X%(),Y$())
F%=X%(0)+LEN(Y$(0))
END FUNCTION'''
    assert BasicMachine(source).run() == '9\n'


def test_array_bounds_and_unknown_array():
    with pytest.raises(BasicError, match='fuera de rango'):
        BasicMachine('OPTION BASE 1\nDIM A%(2)\nPRINT A%(0)').run()
    with pytest.raises(BasicError, match='Arreglo no declarado'):
        BasicMachine('A%(1)=5').run()


def test_array_parameter_type_checked():
    code = '''DIM N%(2)
PRINT F%(N%())
END
FUNCTION F%(S$())
F%=1
END FUNCTION'''
    with pytest.raises(BasicError, match='tipo de arreglo incompatible'):
        BasicMachine(code).run()


def test_inkey_still_reads_once_per_occurrence():
    from basic_cde.core.machine import KeyboardBuffer
    k = KeyboardBuffer()
    k.push('ab')
    assert BasicMachine('PRINT INKEY$; INKEY$()', keyboard=k).run() == 'ab\n'


def test_original_utiles_array_declaration():
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).exists():
        pytest.skip('Configurar BAS_CORPUS_ZIP con el archivo original')
    with ZipFile(archive) as z:
        lib = z.read('utiles.bas').decode('utf-8-sig')
    m = BasicMachine('END', libraries=[lib])
    assert m.routines['MENUELEGIR%'][2][:3] == [
        'ATAJOS%()', 'TEXTOS$()', 'DESTINOS$()'
    ]
