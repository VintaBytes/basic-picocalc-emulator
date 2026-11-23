"""Pruebas unitarias basadas en constructos presentes en LUNAR."""
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import evaluate


def test_if_else_elseif_nested():
    code = '''IF 0 THEN
PRINT "MAL"
ELSEIF 0 THEN
PRINT "MAL2"
ELSEIF 1 THEN
IF 1 THEN
PRINT "BIEN"
ELSE
PRINT "MAL3"
ENDIF
ELSE
PRINT "MAL4"
ENDIF'''
    assert BasicMachine(code).run() == 'BIEN\n'


def test_do_loop_exit():
    code = '''I=0
DO
I=I+1
IF I=3 THEN
EXIT DO
ENDIF
LOOP
PRINT I'''
    assert BasicMachine(code).run() == '3\n'


def test_do_loop_until_and_while():
    code = '''I=0
DO
I=I+1
LOOP UNTIL I=2
DO WHILE I<4
I=I+1
LOOP
PRINT I'''
    assert BasicMachine(code).run() == '4\n'


def test_labels_gosub_and_comments():
    code = '''GOSUB Calculo
PRINT R
END
Calculo:
R=7 ' comentario
RETURN'''
    assert BasicMachine(code).run() == '7\n'


def test_print_functions_and_quotes():
    code = '''A$=UCASE$("hola")
PRINT A$; " ";RJUST$("3",2)
PRINT STRING$(3,"-")'''
    assert BasicMachine(code).run() == 'HOLA  3\n---\n'


def test_input_comma_style():
    m = BasicMachine('INPUT "GASTO: ", G\nPRINT G')
    assert m.run(input_provider=lambda prompt: '12') == '12\n'


def test_expressions_extended():
    assert evaluate('LEFT$("12345",2)') == '12'
    assert evaluate('MID$("ABCDE",2,3)') == 'BCD'
    assert evaluate('RGB(GREEN)') == 0x00FF00
    assert evaluate('RND()') >= 0


def test_inline_if_does_not_shift_block_positions():
    code = '''I=0
DO
I=I+1
IF I=2 THEN EXIT DO
LOOP
IF I=2 THEN
PRINT "OK"
ENDIF'''
    assert BasicMachine(code).run() == 'OK\n'
