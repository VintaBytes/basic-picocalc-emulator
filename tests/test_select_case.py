"""Pruebas de SELECT CASE para compatibilidad con Sokoban/PicoMite."""
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_numeric_and_else():
    program = """FOR X=0 TO 3
SELECT CASE X
CASE 0
PRINT "CERO"
CASE 1, 2
PRINT "MEDIO"
CASE ELSE
PRINT "RESTO"
END SELECT
NEXT X"""
    assert BasicMachine(program).run() == 'CERO\nMEDIO\nMEDIO\nRESTO\n'


def test_case_string_functions_and_no_fallthrough():
    code = '''A$=CHR$(128)
SELECT CASE A$
CASE "a",CHR$(128)
PRINT "OK"
CASE CHR$(129)
PRINT "ERROR"
END SELECT
PRINT "FIN"'''
    assert BasicMachine(code).run() == 'OK\nFIN\n'


def test_nested_with_if_and_select():
    code = """X=2
SELECT CASE X
CASE 1
PRINT "MAL"
CASE 2
IF X=2 THEN
 SELECT CASE X
 CASE 1
 PRINT "MAL2"
 CASE 2
 PRINT "BIEN"
 END SELECT
ENDIF
CASE ELSE
PRINT "MAL3"
END SELECT"""
    assert BasicMachine(code).run() == 'BIEN\n'


def test_is_to_and_multiple_conditions():
    code = """FOR X=1 TO 5
SELECT CASE X
CASE IS < 2
PRINT "UNO"
CASE 2 TO 4
PRINT "CENTRO"
CASE IS >= 5
PRINT "CINCO"
END SELECT
NEXT X"""
    assert BasicMachine(code).run() == 'UNO\nCENTRO\nCENTRO\nCENTRO\nCINCO\n'


def test_case_in_subroutine():
    code = """DRAW 2
END
SUB DRAW TILE
SELECT CASE TILE
 CASE 0
 PRINT "FLOOR"
 CASE 2,5
 PRINT "BOX"
 CASE 4
 PRINT "PLAYER"
END SELECT
END SUB"""
    assert BasicMachine(code).run() == 'BOX\n'


def test_bad_select_structure():
    with pytest.raises(BasicError, match='CASE sin SELECT'):
        BasicMachine('CASE 1\nPRINT "X"')
    with pytest.raises(BasicError, match='SELECT sin cerrar'):
        BasicMachine('SELECT CASE X\nCASE 1\nPRINT "X"')


def test_unmatched_case_does_not_evaluate_malformed_expressions():
    code = '''X=1
SELECT CASE X
CASE 1
PRINT "OK"
CASE VARIABLE_DESCONOCIDA(2)
PRINT "NO"
END SELECT'''
    assert BasicMachine(code).run() == 'OK\n'


def test_sokoban_real_parses_select_case_from_original_corpus():
    """Usa el corpus original cuando está disponible, sin modificarlo."""
    import os
    import zipfile
    from pathlib import Path

    archive = Path(os.environ.get('BAS_CORPUS_ZIP', '/nonexistent/bas.zip'))
    if not archive.exists():
        pytest.skip('Archivo original de la SD no configurado')
    with zipfile.ZipFile(archive) as z:
        source = z.read('juegosg/sokoban.bas').decode('utf-8-sig')
        library = z.read('utiles.bas').decode('utf-8-sig')
    machine = BasicMachine(source, libraries=(library,))
    assert len(machine.select_blocks) >= 7
    # La rutina de portada debe alcanzar SAVE IMAGE con SELECT CASE activo.
    # Se comprueba en el motor sin necesidad de disco ni GUI.
    for _ in range(5000):
        result = machine.step()
        if result.graphics and result.graphics[0] == 'save_image':
            assert result.graphics[1] == 'portada.bmp'
            break
    else:
        pytest.fail('Sokoban no alcanzo SAVE IMAGE')
