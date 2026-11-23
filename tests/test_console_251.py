"""Comparaciones de READY con el firmware PicoCalc 6.0003."""
from pathlib import Path
import pytest

from basic_cde.app.direct import DirectConsole
from basic_cde.app.file_listing import files_listing
from basic_cde.app.memory_report import memory_report
from basic_cde.devices.drives import VirtualDrives
from basic_cde.devices.display import BitmapDisplay
from basic_cde.core.machine import BasicMachine


def test_drive_selection_from_ready(tmp_path):
    a = tmp_path / 'flash'
    b = tmp_path / 'sd'
    a.mkdir()
    b.mkdir()
    (b / 'games').mkdir()
    (b / 'games' / 'test.bas').write_text('PRINT 7')
    drives = VirtualDrives(a=a, b=b)
    console = DirectConsole()
    assert console.execute('b:').action == 'drive'
    drives.drive(console.execute('b:').argument)
    assert drives.cwd_string == 'B:/'
    drives.chdir('games')
    assert drives.cwd_string == 'B:/games'
    drives.drive(console.execute('a:').argument)
    assert drives.cwd_string == 'A:/'
    drives.drive(console.execute('B:').argument)
    assert drives.cwd_string == 'B:/games'
    assert console.execute('DRIVE "A:"').argument == 'A:'
    assert console.execute('CHDIR "B:/games"').argument == 'B:/games'


def test_unmounted_drive_rejected(tmp_path):
    drives = VirtualDrives(a=tmp_path)
    with pytest.raises(Exception, match='sin montar'):
        drives.drive('B:')


def test_listing_format_avoids_leaving_root(tmp_path):
    a = tmp_path / 'flash'
    a.mkdir()
    (a / 'SUB').mkdir()
    (a / 'TEST.BAS').write_text('PRINT 1\n')
    drives = VirtualDrives(a=a)
    txt = files_listing(drives)
    assert txt.startswith('A:/\n')
    assert '<DIR> SUB' in txt
    assert 'TEST.BAS' in txt
    assert '3 directories, 1 files,' in txt
    assert '<DIR> .' in txt
    assert '<DIR> ..' in txt
    assert 'bytes free' in txt


def test_memory_sections_from_pico_60003():
    machine = BasicMachine('A=123')
    machine.step()
    output = memory_report('PRINT 5\n', machine.variables)
    assert 'Program:' in output
    assert 'Library:' in output
    assert 'Saved Variables:' in output
    assert 'RAM:' in output
    assert '208K (100%) Free' in output
    assert '16K (100%) Free' in output
    assert '256K' not in output or 'Free' in output


def test_default_green_can_be_overridden():
    display = BitmapDisplay()
    assert display.foreground == 0x00FF00
    display.console('A')
    assert bytes((0,255,0,255)) in display.framebuffer.snapshot()
    display.graphics(('color', 0xFFFFFF, 0x000000))
    assert display.foreground == 0xFFFFFF
