"""Las funciones TRIM se definen en BASIC; no son intrínsecas PicoMite."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


LIBRARY = '''FUNCTION LTRIM$(S$)
 LTRIM$ = MID$(S$,2)
END FUNCTION
FUNCTION RTRIM$(S$)
 RTRIM$ = LEFT$(S$,LEN(S$)-1)
END FUNCTION
FUNCTION TRIM$(S$)
 TRIM$ = RTRIM$(LTRIM$(S$))
END FUNCTION'''


def test_trim_not_native():
    with pytest.raises(BasicError, match='FUNCTION no disponible: LTRIM'):
        BasicMachine('PRINT LTRIM$(" hola")\nEND').run()


def test_library_trim_is_called():
    assert BasicMachine('PRINT TRIM$(" hola ")\nEND', libraries=[LIBRARY]).run() == 'hola\n'


def test_main_trim_collides_with_library_and_is_rejected():
    main = '''PRINT LTRIM$("abc")
END
FUNCTION LTRIM$(S$)
 LTRIM$ = "MAIN:"+S$
END FUNCTION'''
    with pytest.raises(BasicError, match=r'Rutina duplicada: LTRIM\$'):
        BasicMachine(main, libraries=[LIBRARY])


def test_duplicate_routines_within_main_remain_errors():
    main = '''FUNCTION LTRIM$(S$)
 LTRIM$=S$
END FUNCTION
FUNCTION LTRIM$(X$)
 LTRIM$=X$
END FUNCTION'''
    with pytest.raises(BasicError, match='Rutina duplicada: LTRIM'):
        BasicMachine(main)


def test_duplicate_routines_between_libraries_remain_errors():
    with pytest.raises(BasicError, match='Rutina duplicada: LTRIM'):
        BasicMachine('END', libraries=[LIBRARY, LIBRARY])


def test_homografica2_original_with_utiles_reports_duplicate():
    path = os.getenv('BAS_CORPUS_ZIP')
    if not path or not Path(path).is_file():
        pytest.skip('Definir BAS_CORPUS_ZIP')
    with ZipFile(path) as archive:
        main = archive.read('mate/homografica2.bas').decode('utf-8-sig')
        lib = archive.read('utiles.bas').decode('utf-8-sig')
    with pytest.raises(BasicError, match=r'Rutina duplicada: LTRIM\$'):
        BasicMachine(main, libraries=[lib])
