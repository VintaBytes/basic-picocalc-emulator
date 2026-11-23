"""Regresiones de KILL/RENAME/COPY/MKDIR/RMDIR y prompt de PCC 6.00.03.

Todos los efectos destructivos se limitan a tmp_path (nunca SD del usuario).
"""
from pathlib import Path
import pytest
from basic_cde.core.machine import BasicMachine
from basic_cde.devices.drives import VirtualDrives
from basic_cde.core.expressions import BasicError


def execute(src, a, b=None, input_provider=None):
    return BasicMachine(src, drives=VirtualDrives(a=a, b=b)).run(input_provider=input_provider)


def test_pcc_kill_file_by_array_reference(tmp_path):
    (tmp_path/'throwaway.bas').write_text('ABC')
    execute('''DIM FILE$(2)
FILE$(1)="throwaway.bas"
SEL=1
KILL FILE$(SEL)
END''', tmp_path)
    assert not (tmp_path/'throwaway.bas').exists()


def test_kill_rejects_directories_and_missing(tmp_path):
    (tmp_path/'folder').mkdir()
    for code in ('KILL "folder"', 'KILL "missing.bas"', 'KILL "*.bas"'):
        with pytest.raises(BasicError, match='KILL'):
            execute(code, tmp_path)
    assert (tmp_path/'folder').is_dir()


def test_rename_existing_file_and_prevent_overwrite(tmp_path):
    (tmp_path/'one.bas').write_text('ONE')
    (tmp_path/'used.bas').write_text('USED')
    execute('NEW$="new.bas"\nRENAME "one.bas" AS NEW$\nEND',tmp_path)
    assert (tmp_path/'new.bas').read_text() == 'ONE'
    assert not (tmp_path/'one.bas').exists()
    with pytest.raises(BasicError, match='destino existente'):
        execute('RENAME "new.bas" AS "used.bas"',tmp_path)
    assert (tmp_path/'used.bas').read_text() == 'USED'


def test_copy_between_drives_preserves_source_and_blocks_overwrite(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b';a.mkdir();b.mkdir()
    (a/'copyme.bas').write_bytes(b'example\0\xff')
    execute('COPY "copyme.bas" TO "B:/copyme.bas"',a,b)
    assert (a/'copyme.bas').read_bytes() == (b/'copyme.bas').read_bytes()
    with pytest.raises(BasicError,match='destino existente'):
        execute('COPY "copyme.bas" TO "B:/copyme.bas"',a,b)


def test_mkdir_rmdir_empty_and_protect_nonempty(tmp_path):
    execute('MKDIR "newfolder"\nEND',tmp_path)
    assert (tmp_path/'newfolder').is_dir()
    (tmp_path/'newfolder'/'important.bas').write_text('do not delete')
    with pytest.raises(BasicError, match='RMDIR'):
        execute('RMDIR "newfolder"',tmp_path)
    assert (tmp_path/'newfolder'/'important.bas').read_text() == 'do not delete'
    (tmp_path/'newfolder'/'important.bas').unlink()
    execute('RMDIR "newfolder"',tmp_path)
    assert not (tmp_path/'newfolder').exists()


def test_cannot_escape_virtual_drive(tmp_path):
    a=tmp_path/'sd';a.mkdir()
    (tmp_path/'outside.txt').write_text('safe')
    (a/'link').symlink_to(tmp_path)
    for command in ('KILL "../outside.txt"', 'KILL "link/outside.txt"',
                    'RENAME "link/outside.txt" AS "x.txt"',
                    'COPY "link/outside.txt" TO "new.txt"'):
        with pytest.raises(BasicError):
            execute(command,a)
    assert (tmp_path/'outside.txt').read_text()=='safe'


def test_input_empty_prompt_semicolon_does_not_print_variable_name():
    m=BasicMachine('INPUT ""; inputString$\nPRINT "["; inputString$; "]"\nEND')
    result=m.step()
    assert result.state=='waiting_input'
    assert result.prompt=='? '
    m.input_value('nuevo_nombre.bas')
    assert m.run() == '[nuevo_nombre.bas]\n'


def test_input_comma_suppresses_question_mark():
    m=BasicMachine('INPUT "Escriba: ", X$')
    assert m.step().prompt == 'Escriba: '


def test_input_semicolon_generates_question_mark():
    m=BasicMachine('INPUT "Escriba: "; X$')
    assert m.step().prompt == 'Escriba: ? '


def test_pcc_dialog_real_input_prompt(tmp_path):
    source=(Path(__file__).parent.parent/'examples'/'pcc-273-ajustado.bas').read_text()
    assert 'Input ""; inputString$' in source
    # Input se ejecuta dentro de Dialog: debe pedir entrada sin mostrar el nombre interno.
    m=BasicMachine('INPUT ""; inputString$\nPRINT INPUTSTRING$')
    assert m.step().prompt=='? '
    m.input_value('archivo2.bas')
    assert m.run()=='archivo2.bas\n'


def test_on_error_ignore_1_catches_failed_kill(tmp_path):
    result=execute('ON ERROR IGNORE 1\nKILL "no-existe.bas"\nPRINT MM.ERRNO',tmp_path)
    assert result.strip() == '1'
