"""Regresiones MMBasic: DIM rectangular y paso por referencia."""
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_sokoban_board_two_dimensions():
    code = '''DIM TABLERO(21,16)
TABLERO(0,0)=2
TABLERO(21,16)=7
TABLERO(1,16)=9
PRINT TABLERO(0,0);",";TABLERO(21,16);",";TABLERO(1,16);",";TABLERO(0,1)
END'''
    assert BasicMachine(code).run() == '2,7,9,0\n'


def test_option_base_one_and_three_dimensions():
    code = '''OPTION BASE 1
DIM N%(2,3,4)
N%(1,1,1)=10
N%(2,3,4)=20
PRINT N%(1,1,1)+N%(2,3,4)
END'''
    assert BasicMachine(code).run() == '30\n'


def test_multiple_declarations_and_expression_bounds():
    code = '''N=3
DIM A(N,2), B$(1,1)
A(3,2)=4
B$(1,0)="OK"
PRINT A(3,2);B$(1,0)
END'''
    assert BasicMachine(code).run() == '4OK\n'


def test_array_by_reference_multidimensional():
    code = '''DIM TABLERO(21,16)
MARCAR TABLERO()
PRINT TABLERO(21,16)
END
SUB MARCAR(T())
T(21,16)=88
END SUB'''
    assert BasicMachine(code).run() == '88\n'

@pytest.mark.parametrize('code,match', [
    ('DIM T(2,2)\nPRINT T(2)', 'se esperaban 2 indices'),
    ('DIM T(2,2)\nT(0,0,0)=3', 'se esperaban 2 indices'),
    ('OPTION BASE 1\nDIM T(2,2)\nPRINT T(0,1)', 'fuera de rango'),
    ('DIM T(2,2)\nT(1.3,1)=4', 'Indice invalido'),
    ('DIM T(2,2)\nT(1,3)=4', 'fuera de rango'),
    ('DIM T(2,2)\nT(1,1)="hola"', 'Tipo incorrecto'),
    ('DIM T(1000,1000)', 'demasiado grande'),
    ('DIM T(1,1,1,1,1,1,1,1,1)', 'dimensiones invalido'),
    ('DIM T(2,1.5)', 'limite no entero'),
])
def test_invalid_dimensions_indices(code, match):
    with pytest.raises(BasicError, match=match):
        BasicMachine(code).run()


def test_bas_original_declaration_only():
    from pathlib import Path
    from zipfile import ZipFile
    import os
    archive = Path(os.environ.get('BAS_CORPUS_ZIP', ''))
    if not os.environ.get('BAS_CORPUS_ZIP'):
        pytest.skip('Configurar BAS_CORPUS_ZIP para usar el original')
    if not archive.exists():
        pytest.skip('El corpus original no esta disponible en este entorno')
    with ZipFile(archive) as z:
        source = z.read('juegosg/sokoban.bas').decode('utf-8-sig')
    m = BasicMachine(source)
    # La instruccion 6 DIM es parte del codigo fuente original.
    index = next(i for i, (_, line) in enumerate(m.program) if line.upper().startswith('DIM TABLERO('))
    # Procesar OPTION BASE y el DIM en el orden original.
    m._pending_fonts.clear()
    m.pc = index - 1
    assert m.step().state == 'running'
    assert m.option_base == 1
    result = m.step()
    assert result.state == 'running'
    assert m.variables['TABLERO'].shape == (21, 16)
