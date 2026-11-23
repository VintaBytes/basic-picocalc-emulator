"""Errores claros cuando el BAS acaba en una SUB sin cerrar."""
import os
from pathlib import Path
from zipfile import ZipFile
import pytest

from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine


def test_missing_end_sub_before_library_reports_original_routine():
    source = 'END\nSUB PEDIR_DATOS(A)\n  PRINT A\n'
    library = 'SUB ENCABEZADO()\nEND SUB\n'
    with pytest.raises(BasicError, match=r'PEDIR_DATOS sin END SUB.*linea fuente 2.*antes de cargar la biblioteca'):
        BasicMachine(source, libraries=[library])


def test_missing_end_sub_without_library_reports_declared_line():
    with pytest.raises(BasicError, match=r'PEDIR_DATOS sin END SUB.*linea fuente 2'):
        BasicMachine('END\nSUB PEDIR_DATOS()\nPRINT "x"')


def test_actual_nested_sub_remains_forbidden():
    code = 'SUB A()\nSUB B()\nEND SUB\nEND SUB'
    with pytest.raises(BasicError, match=r'Rutinas anidadas no admitidas.*linea fuente 2.*dentro de A'):
        BasicMachine(code)


def test_log_directa_original_truncation_and_manual_closure():
    path = os.environ.get('BAS_CORPUS_ZIP')
    if not path or not Path(path).is_file():
        pytest.skip('Configurar BAS_CORPUS_ZIP')
    with ZipFile(path) as z:
        source = z.read('mate/log_1_directa.bas').decode('utf-8-sig')
        lib = z.read('utiles.bas').decode('utf-8-sig')
    with pytest.raises(BasicError, match=r'PEDIR_DATOS sin END SUB.*linea fuente 123'):
        BasicMachine(source, libraries=[lib])
    fixed = source + '\nEND SUB\n'
    machine = BasicMachine(fixed, libraries=[lib])
    assert 'PEDIR_DATOS' in machine.routines
