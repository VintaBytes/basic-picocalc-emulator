"""Regresiones de LONGSTRING/JSON$ en la VM, sin emular periféricos."""
import pytest

from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def execute(script):
    return BasicMachine(script + '\nEND').run().splitlines()


def test_length_extract_find_and_ascii_bytes():
    assert execute('''DIM INTEGER A%(32)
LONGSTRING LOAD A%(), 5, "HOLA!"
PRINT LLEN(A%())
PRINT LGETSTR$(A%(), 1, 5)
PRINT LGETBYTE(A%(), 2)
PRINT LINSTR(A%(), "LA")
PRINT LINSTR(A%(), "NO")''') == ['5', 'HOLA!', '79', '3', '0']


def test_append_copy_concat_and_longer_than_255():
    assert execute('''DIM INTEGER A%(200), B%(200)
LONGSTRING APPEND A%(), STRING$(250,"Q")
LONGSTRING APPEND A%(), STRING$(250,"Z")
LONGSTRING COPY B%(), A%()
LONGSTRING CONCAT B%(), A%()
PRINT LLEN(A%())
PRINT LLEN(B%())
PRINT LGETSTR$(B%(),248,6)''') == ['500', '1000', 'QQQZZZ']


def test_slice_and_case():
    assert execute('''DIM INTEGER A%(32), B%(32)
LONGSTRING LOAD A%(), 11, "Hola MUNDO!"
LONGSTRING UCASE A%()
LONGSTRING MID B%(), A%(), 6, 5
PRINT LGETSTR$(B%(),1,5)
LONGSTRING RIGHT B%(), A%(), 6
PRINT LGETSTR$(B%(),1,6)
LONGSTRING LEFT B%(), A%(), 4
LONGSTRING LCASE B%()
PRINT LGETSTR$(B%(),1,4)''') == ['MUNDO', 'MUNDO!', 'hola']


def test_resize_setbyte_clear():
    assert execute('''DIM INTEGER A%(10)
LONGSTRING LOAD A%(), 3, "abc"
LONGSTRING SETBYTE A%(), 2, 88
PRINT LGETSTR$(A%(),1,3)
LONGSTRING RESIZE A%(), 5
PRINT LLEN(A%())
PRINT LGETBYTE(A%(),4)
LONGSTRING CLEAR A%()
PRINT LLEN(A%())''') == ['aXc', '5', '0', '0']


def test_raw_integer_array_overlay_including_word_zero():
    assert execute('''DIM INTEGER A%(10)
LONGSTRING LOAD A%(), 3, "ABC"
PRINT A%(0)
PRINT A%(1)
LONGSTRING CLEAR A%()
PRINT A%(0)''') == ['3', '4407873', '0']


def test_json_nested_paths():
    js = '{"user":{"name":"Pico","data":[7,8],"enabled":true}}'
    encoded = js.replace('"', '""')
    program = f'''DIM INTEGER A%(64)
J$="{encoded}"
LONGSTRING LOAD A%(), LEN(J$), J$
PRINT JSON$(A%(),"user.name")
PRINT JSON$(A%(),"user.data[1]")
PRINT JSON$(A%(),"user.enabled")'''
    assert execute(program) == ['Pico', '8', 'true']


def test_invalid_arguments_are_not_silently_accepted():
    examples = [
        'LONGSTRING CLEAR MISSING()',
        'DIM FLOAT A(20)\nLONGSTRING CLEAR A()',
        'DIM INTEGER A%(3,3)\nLONGSTRING CLEAR A%()',
        'DIM INTEGER A%(3)\nLONGSTRING LOAD A%(), 40, STRING$(40,"A")',
        'DIM INTEGER A%(3)\nLONGSTRING SETBYTE A%(), 1, 256',
        'DIM INTEGER A%(3)\nPRINT LGETBYTE(A%(),1)',
        'DIM INTEGER A%(3)\nPRINT JSON$(A%(),"missing")',
    ]
    for program in examples:
        with pytest.raises(BasicError):
            execute(program)


def test_mid_optional_length_and_1_based_offset():
    assert execute('''DIM INTEGER A%(30), B%(30)
LONGSTRING LOAD A%(), 6, "abcdef"
LONGSTRING MID B%(), A%(), 4
PRINT LGETSTR$(B%(),1,3)
PRINT LINSTR(B%(),"f",2)''') == ['def', '3']


def test_array_prefix_types_and_length_validation():
    assert execute('''DIM INTEGER A(10)
LONGSTRING APPEND A(), "OK"
PRINT LLEN(A())''') == ['2']


def test_no_mutation_when_capacity_exceeded():
    machine = BasicMachine('DIM INTEGER A%(1)\nLONGSTRING LOAD A%(), 5, "hello"\nLONGSTRING APPEND A%(), "12345"\nEND')
    assert machine.step().state == 'running'
    assert machine.step().state == 'running'
    with pytest.raises(BasicError):
        machine.step()
    assert machine.variables['A%'].items[0] == 5
