"""Guardado de imagen real desde el framebuffer unico, sin Qt."""
import struct
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives
from basic_cde.devices.framebuffer import Framebuffer


def _pixel_bmp(bmp, x, y):
    width, height = struct.unpack_from('<ii', bmp, 18)
    stride = (width * 3 + 3) & ~3
    offset = 54 + (height - 1 - y) * stride + x * 3
    return tuple(reversed(bmp[offset:offset+3]))


def test_bmp_header_size_colors_padding_and_bottom_up():
    fb = Framebuffer(3, 2)
    fb.pixel(0, 0, 255, 0, 0)
    fb.pixel(2, 1, 0, 255, 64)
    bmp = fb.to_bmp()
    assert bmp[:2] == b'BM'
    assert struct.unpack_from('<I', bmp, 2)[0] == len(bmp) == 54 + 12 * 2
    assert struct.unpack_from('<H', bmp, 28)[0] == 24
    assert _pixel_bmp(bmp, 0, 0) == (255, 0, 0)
    assert _pixel_bmp(bmp, 2, 1) == (0, 255, 64)
    assert _pixel_bmp(bmp, 1, 0) == (0, 0, 0)


def test_save_image_uses_latest_graphics_and_print(tmp_path):
    sd = tmp_path / 'sd'
    (sd / 'games').mkdir(parents=True)
    drives = VirtualDrives(b=sd)
    drives.chdir('B:/games')
    source = '''CLS RGB(4,5,6)
PIXEL 200,100,RGB(255,0,128)
PRINT "A"
SAVE IMAGE "screen.bmp"
END'''
    session = BasicSession(source, drives=drives)
    for _ in range(20):
        result = session.step()
        if result.state == 'finished':
            break
    else:
        pytest.fail('La ejecucion no termino')
    bmp = (sd / 'games' / 'screen.bmp').read_bytes()
    assert _pixel_bmp(bmp, 200, 100) == (255, 0, 128)
    assert _pixel_bmp(bmp, 319, 319) == (4, 5, 6)
    # El texto PRINT modifica la primera fila desde CLS.
    assert any(_pixel_bmp(bmp, x, y) != (4, 5, 6)
               for y in range(0, 12) for x in range(0, 8))
    assert len(bmp) == 54 + 320 * 320 * 3
    assert session.display.framebuffer.get_pixel(200, 100) == (255, 0, 128, 255)


def test_save_image_requires_mount_and_stays_within_root(tmp_path):
    no_mount = BasicSession('SAVE IMAGE "x.bmp"')
    with pytest.raises(BasicError, match='unidad montada'):
        no_mount.step()
    sd = tmp_path / 'sd'
    sd.mkdir()
    for name in ('../escape.bmp', 'B:/../escape.bmp', 'x.bas'):
        session = BasicSession(f'SAVE IMAGE "{name}"', drives=VirtualDrives(b=sd))
        with pytest.raises(BasicError):
            session.step()
    assert not (tmp_path / 'escape.bmp').exists()


def test_save_image_does_not_escape_through_symlink(tmp_path):
    sd = tmp_path / 'sd'
    dest = tmp_path / 'outside'
    sd.mkdir()
    dest.mkdir()
    (sd / 'link').symlink_to(dest, target_is_directory=True)
    disks = VirtualDrives(b=sd)
    disks.drive('B:')
    with pytest.raises(BasicError, match='fuera'):
        BasicSession('SAVE IMAGE "link/escape.bmp"', drives=disks).step()
    assert not (dest / 'escape.bmp').exists()


def test_original_sokoban_saves_portada_when_corpus_available(tmp_path):
    archive = os.getenv('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).exists():
        pytest.skip('Corpus original no disponible')
    with ZipFile(archive) as z:
        original = z.read('juegosg/sokoban.bas').decode('utf-8-sig')
        lib = z.read('utiles.bas').decode('utf-8-sig')
    sd = tmp_path / 'sd'
    (sd / 'juegosg').mkdir(parents=True)
    drives = VirtualDrives(b=sd)
    drives.chdir('B:/juegosg')
    session = BasicSession(original, drives=drives, libraries=[lib])
    for _ in range(10000):
        result = session.step()
        if (sd / 'juegosg' / 'portada.bmp').exists():
            break
        if result.state == 'finished':
            pytest.fail('Sokoban termino antes de SAVE IMAGE')
    else:
        pytest.fail('Sokoban no llego a SAVE IMAGE')
    path = sd / 'juegosg' / 'portada.bmp'
    assert path.read_bytes()[:2] == b'BM'
    assert len(path.read_bytes()) == 54 + 320 * 320 * 3
