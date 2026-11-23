"""Menu de juegos original + biblioteca reales, sin cambiar archivos BASIC."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest
from basic_cde.app.session import BasicSession
from basic_cde.devices.drives import VirtualDrives


def test_real_graphics_menu_accepts_escape_and_chains(tmp_path):
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Configurar BAS_CORPUS_ZIP')
    with ZipFile(archive) as zipped:
        menu = zipped.read('juegosg/menu.bas').decode('utf-8-sig')
        library = zipped.read('utiles.bas').decode('utf-8-sig')
    base = tmp_path / 'sd' / 'bas'
    (base / 'juegosg').mkdir(parents=True)
    (base / 'menu.bas').write_text('PRINT "MENU RAIZ"\nEND\n', encoding='utf-8')
    drives = VirtualDrives(b=base.parent)
    drives.chdir('B:/bas/juegosg')
    session = BasicSession(menu, drives=drives, libraries=[library])
    # Dejar que MenuElegir entre en polling de INKEY$ sin PAUSE.
    for _ in range(50):
        assert session.step().state == 'running'
    session.machine.keyboard.push(chr(27))
    output = ''
    for _ in range(4000):
        result = session.step()
        output += result.output
        if result.state == 'finished':
            break
    else:
        pytest.fail('El menu no completo la transferencia despues de ESC')
    assert 'MENU RAIZ' in output
    assert session.chain_count == 1
    assert session.active_path == base / 'menu.bas'
