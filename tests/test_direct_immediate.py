"""Comandos READY y sentencias inmediatas: comparten el motor real."""
import pytest

from basic_cde.app.direct import DirectConsole, DirectCommandError, DirectExecutor
from basic_cde.devices.display import BitmapDisplay
from basic_cde.core.expressions import BasicError


def execute(console, executor, command):
    result = console.execute(command)
    assert result.action == 'immediate'
    return executor.execute(result.argument)


def output(results):
    return ''.join(result.output for result in results)


def test_immediate_print_and_shorthand_without_program():
    console = DirectConsole()
    executor = DirectExecutor()
    assert output(execute(console, executor, 'PRINT 2+2')) == '4\n'
    assert output(execute(console, executor, '? "PicoCalc"')) == 'PicoCalc\n'
    assert output(execute(console, executor, 'PRINT')) == '\n'
    assert console.execute('LIST').message == ''


def test_variables_and_arrays_survive_between_commands():
    console = DirectConsole('10 PRINT "EN MEMORIA"\n20 END\n')
    executor = DirectExecutor()
    execute(console, executor, 'A=12')
    assert output(execute(console, executor, 'PRINT A+3')) == '15\n'
    execute(console, executor, 'LET TEXTO$="HOLA"')
    assert output(execute(console, executor, 'PRINT TEXTO$')) == 'HOLA\n'
    execute(console, executor, 'DIM VECTOR(4)')
    execute(console, executor, 'VECTOR(1)=42')
    assert output(execute(console, executor, 'PRINT VECTOR(1)')) == '42\n'
    # La memoria BASIC visible por LIST no recibe comandos inmediatos.
    assert console.execute('LIST').message == '10 PRINT "EN MEMORIA"\n20 END\n'
    assert console.execute('RUN').action == 'run'
    assert executor.context.variables.globals['A'] == 12


def test_direct_graphics_use_the_same_device_dispatch():
    console = DirectConsole()
    executor = DirectExecutor()
    display = BitmapDisplay()
    for command in ('COLOR RGB(255,0,0)', 'CLS RGB(0,0,0)',
                    'FONT 7,2', 'TEXT 0,0,"A"', 'PIXEL 100,120,RGB(0,255,0)'):
        for result in execute(console, executor, command):
            if result.graphics:
                display.graphics(result.graphics)
    assert executor.context.foreground == 0xFF0000
    assert display.framebuffer.get_pixel(100, 120) == (0, 255, 0, 255)
    assert display.current_font == 7
    assert display.font_scale == 2


def test_new_does_not_modify_disk_and_reset_removes_variables():
    console = DirectConsole('10 PRINT 1\n')
    executor = DirectExecutor()
    execute(console, executor, 'COUNT=123')
    assert console.execute('NEW').action == 'new'
    assert not console.source
    executor.reset()
    assert 'COUNT' not in executor.context.variables.globals
    assert output(executor.execute('PRINT COUNT')) == '0\n'


def test_refuses_control_flow_in_immediate_mode():
    console = DirectConsole()
    for statement in ('FOR I=1 TO 10', 'INPUT A', 'GOTO 100', 'PAUSE 1000',
                      'RUN 1', 'SAVE "test.bas"'):
        with pytest.raises(DirectCommandError):
            console.execute(statement)
