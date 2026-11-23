from pathlib import Path
import pytest
from basic_cde.devices.drives import detect_sd_root, VirtualDrives
from basic_cde.app.session import BasicSession


def make_sd(tmp_path):
    sd = tmp_path / 'sdcard'
    bas = sd / 'bas'
    (bas / 'juegosg').mkdir(parents=True)
    (bas / 'juegost').mkdir()
    (bas / 'boot.bas').write_text('END\n')
    (bas / 'juegosg' / 'menu.bas').write_text('PRINT "VOLVI AL MENU"\nEND\n')
    return sd, bas


def test_detects_legacy_bas_mount(tmp_path):
    sd, bas = make_sd(tmp_path)
    assert detect_sd_root(bas) == sd
    disks = VirtualDrives(b=detect_sd_root(bas))
    disks.drive('B:')
    disks.chdir('B:/bas/juegosg')
    assert disks.cwd_string == 'B:/bas/juegosg'
    assert disks.load_program('menu.bas')[1] == bas / 'juegosg' / 'menu.bas'


def test_exit_sokoban_chain_to_menu(tmp_path):
    sd, bas = make_sd(tmp_path)
    drives = VirtualDrives(b=detect_sd_root(bas))
    program = 'DRIVE "B:"\nCHDIR "B:/bas/juegosg"\nRUN "menu.bas"\n'
    session = BasicSession(program, drives=drives)
    output = ''
    for _ in range(20):
        result = session.step()
        output += result.output
        if result.state == 'finished':
            break
    else:
        pytest.fail('El encadenado no termino')
    assert 'VOLVI AL MENU' in output
    assert session.chain_count == 1


def test_no_rewrite_on_arbitrary_bas_folder(tmp_path):
    bas = tmp_path / 'bas'
    bas.mkdir()
    (bas / 'juegosg').mkdir()
    assert detect_sd_root(bas) == bas
    other = tmp_path / 'otra'
    other.mkdir()
    assert detect_sd_root(other) == other
