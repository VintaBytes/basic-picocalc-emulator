"""PicoMite: RUN/CHAIN with cmdline and LOAD CONTEXT KEEP."""
import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine
from basic_cde.devices.drives import VirtualDrives


def finish(session, max_steps=200):
    output = []
    for _ in range(max_steps):
        result = session.step()
        output.append(result.output)
        if result.state == "finished":
            return "".join(output)
        assert result.state == "running", result.state
    raise AssertionError("La sesion no finalizo")


def test_run_passes_cmdline_and_clears_previous_variables(tmp_path):
    sd = tmp_path / "sd"
    sd.mkdir()
    (sd / "target.bas").write_text('PRINT MM.CMDLINE$\nPRINT OLD\nEND\n')
    src = '''OLD=42
target$="B:/target.bas"
selectedDate$="2026-11-27"
RUN target$, selectedDate$'''
    session = BasicSession(src, drives=VirtualDrives(b=sd))
    assert finish(session) == "2026-11-27\n0\n"
    assert "OLD" not in session.machine.variables.globals
    assert session.machine.variables.globals["MM.CMDLINE$"] == "2026-11-27"


def test_run_without_second_argument_sets_empty_cmdline(tmp_path):
    sd = tmp_path / "sd"
    sd.mkdir()
    (sd / "target.bas").write_text('PRINT LEN(MM.CMDLINE$)\nEND')
    session = BasicSession('RUN "B:/target.bas"', drives=VirtualDrives(b=sd))
    assert finish(session) == "0\n"


def test_chain_preserves_global_scalars_arrays_and_changes_cmdline(tmp_path):
    sd = tmp_path / "sd"
    sd.mkdir()
    (sd / "target.bas").write_text('''PRINT MM.CMDLINE$
PRINT FLAG
PRINT RECORD$(1)
END''')
    src = '''OPTION BASE 1
DIM RECORD$(2) LENGTH 10
RECORD$(1)="memoria"
FLAG=27
CHAIN "B:/target.bas", "retorno"'''
    session = BasicSession(src, drives=VirtualDrives(b=sd))
    assert finish(session) == "retorno\n27\nmemoria\n"
    arr = session.machine.variables.globals["RECORD$"]
    assert arr.string_length == 10
    assert arr.base == 1


def test_chain_without_arg_sets_empty_cmdline(tmp_path):
    sd = tmp_path / "sd"
    sd.mkdir()
    (sd / "target.bas").write_text('PRINT LEN(MM.CMDLINE$)\nEND')
    session = BasicSession('CHAIN "B:/target.bas"', drives=VirtualDrives(b=sd))
    assert finish(session) == "0\n"


def test_calendar_tasks_roundtrip_without_state_file(tmp_path):
    sd = tmp_path / "sd"
    sd.mkdir()
    (sd / "calendar.bas").write_text('''PRINT "CAL:"+MM.CMDLINE$
RUN "B:/tasks.bas","2026-11-27"
END''')
    (sd / "tasks.bas").write_text('''PRINT "TAREAS:"+MM.CMDLINE$
RUN "B:/back.bas", MM.CMDLINE$
END''')
    (sd / "back.bas").write_text('''PRINT "VUELTA:"+MM.CMDLINE$
END''')
    session = BasicSession('RUN "B:/calendar.bas"', drives=VirtualDrives(b=sd))
    assert finish(session) == ("CAL:\nTAREAS:2026-11-27\n"
                               "VUELTA:2026-11-27\n")


@pytest.mark.parametrize("statement,reason", [
    ('RUN "B:/target.bas", 123', 'cmdline'),
    ('CHAIN "B:/target.bas", 123', 'cmdline'),
    ('RUN "B:/target.bas", "a", "b"', 'archivo'),
    ('CHAIN "B:/target.bas", "a", "b"', 'archivo'),
    ('RUN "B:/target.bas", "' + 'x' * 256 + '"', 'cmdline'),
])
def test_invalid_args_rejected(statement, reason, tmp_path):
    sd = tmp_path / "sd"
    sd.mkdir()
    session = BasicSession(statement, drives=VirtualDrives(b=sd))
    with pytest.raises(BasicError, match=reason):
        session.step()


def test_context_keep_can_load_twice(tmp_path):
    flash = tmp_path / "flash"
    flash.mkdir()
    src = '''A=9
SAVE CONTEXT CLEAR
LOAD CONTEXT KEEP
PRINT A
A=0
LOAD CONTEXT
PRINT A
END'''
    session = BasicSession(src, drives=VirtualDrives(a=flash))
    assert finish(session) == "9\n9\n"
    assert not (flash / ".basic-cde-context.json").exists()


def test_context_keep_retains_file_and_consumed_load_errors(tmp_path):
    flash = tmp_path / "flash"
    flash.mkdir()
    keep = BasicMachine('A=13\nSAVE CONTEXT\nLOAD CONTEXT KEEP\nEND',
                        drives=VirtualDrives(a=flash))
    keep.run()
    assert (flash / ".basic-cde-context.json").exists()
    source = BasicMachine('LOAD CONTEXT\nEND', drives=VirtualDrives(a=flash))
    source.run()
    assert not (flash / ".basic-cde-context.json").exists()
    with pytest.raises(BasicError, match="no hay contexto"):
        BasicMachine("LOAD CONTEXT", drives=VirtualDrives(a=flash)).run()


def test_cmdline_is_a_readonly_predefined_string():
    assert BasicMachine('PRINT LEN(MM.CMDLINE$)\nEND').run() == "0\n"
    for statement in ('MM.CMDLINE$="cambio"', 'LET MM.CMDLINE$="cambio"'):
        with pytest.raises(BasicError, match="solo lectura"):
            BasicMachine(statement + '\nEND').run()
