"""LINE INPUT de consola y retorno a duplicados estrictos."""
import os
from pathlib import Path
from zipfile import ZipFile
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_line_input_with_prompt_accepts_commas_and_whitespace():
    p = BasicMachine('LINE INPUT "Ingrese a,b,c,d: ", linea$\nPRINT "[";linea$;"]"\nEND')
    prompts=[]
    output=p.run(input_provider=lambda prompt: prompts.append(prompt) or '3, 4, -2, 1')
    assert prompts == ['Ingrese a,b,c,d: ']
    assert output == '[3, 4, -2, 1]\n'


def test_line_input_blank_is_empty_string_and_preserves_leading_spaces():
    assert BasicMachine('LINE INPUT CADENA$\nPRINT LEN(CADENA$)').run(input_provider=lambda _: '') == '0\n'
    assert BasicMachine('LINE INPUT "? "; A$\nPRINT "[";A$;"]"').run(input_provider=lambda _: '  Hola  ') == '[  Hola  ]\n'


def test_line_input_rejects_numeric_variable():
    with pytest.raises(BasicError, match='LINE INPUT: sintaxis invalida'):
        BasicMachine('LINE INPUT "dato: ", N').run(input_provider=lambda _: '3')


def test_original_homografica_line38_is_valid_input_syntax():
    archive=os.getenv('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Definir BAS_CORPUS_ZIP')
    with ZipFile(archive) as z:
        original=z.read('mate/homografica2.bas').decode('utf-8-sig')
    assert original.splitlines()[37].strip() == 'LINE INPUT "Ingrese a,b,c,d: ", linea$'
    assert 'LINE INPUT "Ingrese a,b,c,d: ", linea$' in original
