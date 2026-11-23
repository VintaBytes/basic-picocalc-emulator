import pytest
from basic_cde.app.direct import DirectConsole, DirectCommandError


def test_list_and_edit_numbered_lines():
    console = DirectConsole('10 PRINT "HOLA"\n30 END\n')
    assert console.execute('LIST').message == '10 PRINT "HOLA"\n30 END\n'
    console.execute('20 PRINT 123')
    assert console.execute('LIST 15-25').message == '20 PRINT 123\n'
    console.execute('20 PRINT 456')
    assert console.execute('LIST').message == '10 PRINT "HOLA"\n20 PRINT 456\n30 END\n'
    console.execute('20')
    assert console.execute('LIST').message == '10 PRINT "HOLA"\n30 END\n'
    assert console.execute('RUN').action == 'run'


def test_new_and_load_virtual_file():
    console = DirectConsole('10 PRINT 7\n')
    assert console.execute('NEW').modified
    with pytest.raises(DirectCommandError):
        console.execute('RUN')
    cmd = console.execute('LOAD "B:/bas/mate/a.bas"')
    assert (cmd.action, cmd.argument) == ('load', 'B:/bas/mate/a.bas')
    cmd = console.execute('RUN "programa.bas"')
    assert (cmd.action, cmd.argument) == ('run_file', 'programa.bas')


def test_reject_unsupported_and_bad_commands():
    console = DirectConsole('10 PRINT 1\n')
    for line in ('DELETE ALL', 'LOAD file.bas',
                 'LIST hola', 'LIST 50-10', 'NEW extra'):
        with pytest.raises(DirectCommandError):
            console.execute(line)
    assert console.source == '10 PRINT 1\n'


def test_plain_program_listing_and_history():
    console = DirectConsole('PRINT "Hola"\nEND\n')
    assert console.execute('LIST').message == 'PRINT "Hola"\nEND\n'
    assert 'RUN' in console.execute('HELP').message
