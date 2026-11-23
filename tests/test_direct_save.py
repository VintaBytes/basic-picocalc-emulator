"""Comandos SAVE de READY: fichero BAS sin tocar archivos externos."""
import pytest
from basic_cde.app.direct import DirectConsole, DirectCommandError
from basic_cde.devices.drives import VirtualDrives
from basic_cde.core.expressions import BasicError


def test_save_new_load_roundtrip_and_replace(tmp_path):
    root = tmp_path / 'sd'
    (root / 'bas').mkdir(parents=True)
    drives = VirtualDrives(b=root)
    drives.chdir('B:/bas')
    console = DirectConsole('10 PRINT "HOLA"\n20 END\n')
    command = console.execute('save "prueba"')
    assert (command.action, command.argument) == ('save', 'prueba')
    path = drives.save_program(command.argument, console.source)
    assert path == root / 'bas' / 'prueba.bas'
    assert path.read_text(encoding='utf-8') == console.source
    console.execute('NEW')
    assert not console.source
    source, loaded = drives.load_program('prueba')
    assert loaded == path
    assert source == '10 PRINT "HOLA"\n20 END\n'
    console.source = '10 PRINT "CAMBIO"\n'
    drives.save_program('prueba', console.source)
    assert drives.load_program('prueba')[0] == console.source


def test_save_validations_and_no_external_writes(tmp_path):
    root = tmp_path / 'sd'
    root.mkdir()
    drives = VirtualDrives(b=root)
    drives.drive('B:')
    console = DirectConsole('10 END\n')
    for instruction in ('SAVE', 'SAVE prueba.bas', 'SAVE "x" EXTRA'):
        with pytest.raises(DirectCommandError):
            console.execute(instruction)
    with pytest.raises(DirectCommandError, match='No hay programa'):
        DirectConsole().execute('SAVE "vacio"')
    for filename in ('../fuera', 'B:/../fuera', 'malo.txt', 'ausente/uno.bas'):
        with pytest.raises(BasicError):
            drives.save_program(filename, console.source)
    assert not (tmp_path / 'fuera.bas').exists()


def test_save_never_follows_symlink_outside_mount(tmp_path):
    root = tmp_path / 'sd'
    outside = tmp_path / 'outside'
    root.mkdir()
    outside.mkdir()
    (root / 'enlace').symlink_to(outside, target_is_directory=True)
    drives = VirtualDrives(b=root)
    drives.drive('B:')
    with pytest.raises(BasicError, match='fuera'):
        drives.save_program('enlace/peligro.bas', '10 END\n')
    assert not (outside / 'peligro.bas').exists()


def test_save_unmounted_drive_rejected(tmp_path):
    drives = VirtualDrives(a=tmp_path)
    with pytest.raises(BasicError, match='sin montar'):
        drives.save_program('B:/programa.bas', '10 END\n')
