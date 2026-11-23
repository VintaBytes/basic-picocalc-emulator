"""Compatibilidad MMBasic 6.00.03: DATA crudo y cierre de SELECT CASE."""
from basic_cde.core.machine import BasicMachine
from basic_cde.app.session import BasicSession


def drain(machine, limit=100):
    output = []
    for _ in range(limit):
        result = machine.step()
        if result.output:
            output.append(result.output)
        if result.state == 'finished':
            break
    return ''.join(output)


def test_unquoted_data_read_as_string():
    m = BasicMachine('DATA X, XX, UnTexto\nREAD A$,B$,C$\nPRINT A$;B$;C$\nEND')
    assert m.data_values == ['X', 'XX', 'UnTexto']
    drain(m)
    assert m.variables.get('A$') == 'X'
    assert m.variables.get('B$') == 'XX'
    assert m.variables.get('C$') == 'UnTexto'


def test_unquoted_data_does_not_evaluate_variable():
    m = BasicMachine('X=123\nDATA X\nREAD A$\nEND')
    drain(m)
    assert m.variables.get('A$') == 'X'


def test_data_numeric_preserves_number():
    m = BasicMachine('DATA 10, -2, 3.5, "Hola"\nREAD A,B,C,D$\nEND')
    drain(m)
    assert m.variables.get('A') == 10
    assert m.variables.get('B') == -2
    assert m.variables.get('C') == 3.5
    assert m.variables.get('D$') == 'Hola'


def test_select_case_accepts_extra_closing_parenthesis_with_warning():
    source = (
        'DIM Map(2,2,2)\nMap(1,1,1)=7\n'
        'SELECT CASE Map(1,1,1))\n'
        'CASE 7\nPRINT "OK"\n'
        'CASE ELSE\nPRINT "NO"\n'
        'END SELECT\nEND'
    )
    m = BasicMachine(source)
    assert len(m.warnings) == 1
    assert 'linea fuente 3' in m.warnings[0]
    assert 'SELECT CASE' in m.warnings[0]
    assert 'OK' in drain(m)


def test_select_case_valid_has_no_warning():
    m = BasicMachine('SELECT CASE (1+1)\nCASE 2\nPRINT "OK"\nEND SELECT\nEND')
    assert m.warnings == []
    assert 'OK' in drain(m)


def test_warning_is_not_part_of_basic_output():
    s = BasicSession('SELECT CASE (1))\nCASE 1\nPRINT "OK"\nEND SELECT\nEND')
    assert len(s.machine.warnings) == 1
    output = []
    for _ in range(20):
        r = s.step()
        output.append(r.output)
        if r.state == 'finished':
            break
    assert 'Warning' not in ''.join(output)
