import pytest
from basic_cde.app.direct import DirectConsole
from basic_cde.app.memory_report import memory_report
from basic_cde.app.console_banner import startup_lines
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError


def test_direct_commands():
    cmd = DirectConsole('10 PRINT 1\n')
    assert cmd.execute('MEMORY').action == 'memory'
    assert cmd.execute('FILES').action == 'files'
    assert cmd.execute('LIST').message == '10 PRINT 1\n'


def test_memory_counts_program_and_vars():
    machine = BasicMachine('DIM INTEGER B%(2)')
    assert machine.step().state == 'running'
    text = memory_report('10 PRINT 1\n', machine.variables)
    assert 'Program:' in text
    assert 'RAM:' in text
    assert 'Variables' in text
    assert 'Library:' in text
    assert 'Saved Variables:' in text


def test_array_type_name_collision():
    machine = BasicMachine('DIM INTEGER B%(2)\nB$="HOLA"')
    assert machine.step().state == 'running'
    with pytest.raises(BasicError, match='Array Dimensions'):
        machine.step()


def test_banner():
    assert startup_lines(linux_version='0.2.50', loaded_program='testb.bas') == [
        'BASIC PicoCalc Emulator V6.00.03', 'Ariel Palazzesi - Linux v0.2.50',
        'Cargado testb.bas', 'READY']
