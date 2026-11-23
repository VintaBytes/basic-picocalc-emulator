"""Regresiones headless: montajes, bibliotecas y RUN encadenado."""
import pytest
from basic_cde.devices.drives import VirtualDrives
from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError


def output(session, max_steps=1000):
    pieces = []
    for _ in range(max_steps):
        result = session.step()
        pieces.append(result.output)
        if result.state == 'finished':
            return ''.join(pieces)
        if result.state.startswith('waiting'):
            raise AssertionError('Programa de prueba no debe esperar entrada')
    raise AssertionError('Exceso de pasos')


def test_drives_case_and_cwd(tmp_path):
    a, b = tmp_path / 'flash', tmp_path / 'sd'
    a.mkdir(); b.mkdir(); (b / 'Sub').mkdir()
    (b / 'Sub' / 'Menu.bas').write_text('PRINT "OK"\nEND\n')
    (a / 'Menu.bas').write_text('END\n')
    disks = VirtualDrives(a, b)
    assert disks.resolve('Menu.bas').name == 'Menu.bas'
    with pytest.raises(BasicError):
        disks.load_program('menu.bas')
    disks.drive('b:')
    disks.chdir('sub')
    assert disks.cwd_string == 'B:/Sub'
    assert disks.load_program('MENU.BAS')[0].startswith('PRINT')
    disks.chdir('..')
    assert disks.cwd_string == 'B:/'


def test_absolute_drive_and_escape_protection(tmp_path):
    b = tmp_path / 'sd'; b.mkdir()
    (b / 'folder').mkdir()
    other = tmp_path / 'other'; other.mkdir()
    (b / 'link').symlink_to(other, target_is_directory=True)
    disks = VirtualDrives(b=b)
    disks.drive('B:')
    with pytest.raises(BasicError):
        disks.resolve('../other/file.bas')
    with pytest.raises(BasicError):
        disks.resolve('B:/folder/../../other')
    with pytest.raises(BasicError):
        disks.resolve('link/payload.bas')
    with pytest.raises(BasicError):
        disks.resolve('B:folder')
    with pytest.raises(BasicError):
        disks.resolve('C:/file.bas')


def test_chain_preserves_drive_and_has_no_ready(tmp_path):
    b = tmp_path / 'sd'; b.mkdir(); (b / 'juegost').mkdir()
    (b / 'juegost' / 'Menu.BAS').write_text('PRINT "SEGUNDO"\nEND\n')
    source = 'PRINT "PRIMERO"\nDRIVE "B:"\nCHDIR "B:/JUEGOST"\nRUN "menu"\nPRINT "NO"'
    disks = VirtualDrives(b=b)
    session = BasicSession(source, drives=disks)
    assert output(session) == 'PRIMERO\nSEGUNDO\n'
    assert session.chain_count == 1
    assert disks.cwd_string == 'B:/juegost'


def test_failed_chain_keeps_machine(tmp_path):
    b = tmp_path / 'sd'; b.mkdir()
    session = BasicSession('DRIVE "B:"\nRUN "no-existe.bas"\nEND', drives=VirtualDrives(b=b))
    session.step()
    previous = session.machine
    with pytest.raises(BasicError):
        session.step()
    assert session.machine is previous


def test_library_sub_and_function_without_rewriting_source(tmp_path):
    lib = tmp_path / 'utiles.bas'
    lib.write_text('''SUB SALUDAR(T$)
 PRINT T$
END SUB
FUNCTION DOBLE(X)
 DOBLE = X * 2
END FUNCTION
''')
    source = 'SALUDAR "HOLA"\nPRINT DOBLE(4)\nEND'
    s = BasicSession.with_library_files(source, [lib])
    assert output(s) == 'HOLA\n8\n'
    assert lib.read_text().startswith('SUB SALUDAR')


def test_unmounted_disk_is_rejected():
    disks = VirtualDrives()
    with pytest.raises(BasicError):
        disks.drive('B:')
