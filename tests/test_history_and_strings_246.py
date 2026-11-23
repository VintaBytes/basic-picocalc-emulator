"""Terminal history and binary string conversions: PC regression tests."""
import math
import struct
import pytest
from basic_cde.app.history import CommandHistory
from basic_cde.core.expressions import BasicError, evaluate
from basic_cde.core.machine import BasicMachine


def test_ready_history_recalls_and_restores_draft():
    history = CommandHistory()
    history.record('PRINT 1')
    history.record('PRINT 2')
    assert history.previous('PRI') == 'PRINT 2'
    assert history.previous('PRINT 2') == 'PRINT 1'
    assert history.previous('PRINT 1') == 'PRINT 1'
    assert history.next('PRINT 1') == 'PRINT 2'
    assert history.next('PRINT 2') == 'PRI'
    assert history.next('PRI') == 'PRI'


def test_history_ignores_blank_and_repeated_and_limits_size():
    h = CommandHistory(limit=2)
    for command in ('A', 'A', ' ', 'B', 'C'):
        h.record(command)
    assert h.entries == ['B','C']
    assert h.previous('') == 'C'
    assert h.previous('') == 'B'


@pytest.mark.parametrize('typ,num,expected', [
    ('INT8', -1, '\xff'), ('UINT8', 255, '\xff'),
    ('INT16', 258, '\x02\x01'), ('UINT16', 65535, '\xff\xff'),
    ('INT32', -2, '\xfe\xff\xff\xff'),
    ('INT64', -1, '\xff' * 8), ('UINT64', 2**63, '\x00'*7+'\x80'),
])
def test_binary_roundtrip_integers(typ, num, expected):
    vars = {'N': num}
    encoded = evaluate(f'BIN2STR$({typ},N)', vars)
    assert encoded == expected
    assert evaluate(f'STR2BIN({typ},BUF$)', {'BUF$': encoded}) == num
    assert evaluate(f'STR2BIN({typ},BIN2STR$({typ},N))', vars) == num


def test_binary_big_endian_and_ieee_float():
    assert evaluate('BIN2STR$(INT32,258,BIG)') == '\x00\x00\x01\x02'
    assert evaluate('STR2BIN(INT32,BIN2STR$(INT32,258,BIG),BIG)') == 258
    assert evaluate('BIN2STR$(SINGLE,1.5)') == struct.pack('<f',1.5).decode('latin-1')
    assert math.isclose(evaluate('STR2BIN(DOUBLE,BIN2STR$(DOUBLE,3.125))'),3.125)


@pytest.mark.parametrize('expression', [
    'BIN2STR$(INT8,256)', 'BIN2STR$(UINT8,-1)', 'BIN2STR$(INT64,1e100)',
    'BIN2STR$(INT16,5,MIDDLE)', 'BIN2STR$(WRONG,5)',
    'STR2BIN(INT16,"a")', 'STR2BIN(INT8,"XY")', 'STR2BIN(INT16,"áßç")'
])
def test_binary_errors_are_basic_errors(expression):
    with pytest.raises(BasicError):
        evaluate(expression)


def test_val_and_string_numeric_forms():
    assert evaluate('VAL("NOT A NUMBER")') == 0
    assert evaluate('VAL("&HFF")') == 255
    assert evaluate('VAL("&B101010")') == 42
    assert evaluate('VAL("&O17")') == 15
    assert evaluate('STRING$(3,65)') == 'AAA'
    assert evaluate('STRING$(3,"XYZ")') == 'XXX'
    with pytest.raises(BasicError):
        evaluate('STRING$(3,300)')


def test_basic_machine_runs_binary_functions_in_program():
    machine = BasicMachine('A$=BIN2STR$(UINT16,258)\nPRINT STR2BIN(UINT16,A$)\nEND')
    output=[]
    for _ in range(30):
        step = machine.step()
        if step.output:
            output.append(step.output)
        if step.state == 'finished':
            break
    assert '258' in ''.join(output)


def test_qt_history_intercepts_only_ready():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'src/basic_cde/gui/window.py').read_text()
    assert 'self.command_history = CommandHistory()' in text
    assert 'and self.direct_ready and self.isActiveWindow()' in text
    assert 'self.command_history.record(text)' in text
    assert 'self.recall_command(qkey == int(Qt.Key.Key_Up))' in text
    assert 'self.command.setCursorPosition(len(recalled))' in text
