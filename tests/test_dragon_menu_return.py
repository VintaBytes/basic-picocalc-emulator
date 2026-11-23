"""Dragon: distinguir fallo del programa saliente del menu destino."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives


def test_unclosed_blocks_report_source_line():
    with pytest.raises(BasicError, match=r'IF sin cerrar \(linea fuente 1; falta END IF\)'):
        BasicSession('IF 1 THEN\n PRINT "A"')
    with pytest.raises(BasicError, match=r'DO sin cerrar \(linea fuente 1; falta LOOP\)'):
        BasicSession('DO\n PRINT "A"')
    with pytest.raises(BasicError, match=r'SELECT sin cerrar \(linea fuente 1; falta END SELECT\)'):
        BasicSession('SELECT CASE 1\nCASE 1\n PRINT "A"')


def test_sd_root_menu_reports_real_unclosed_if():
    corpus = os.environ.get('BAS_CORPUS_ZIP')
    if not corpus or not Path(corpus).is_file():
        pytest.skip('Se requiere BAS_CORPUS_ZIP')
    with ZipFile(corpus) as archive:
        main_menu = archive.read('menu.bas').decode('latin1')
        library = archive.read('utiles.bas').decode('latin1')
    with pytest.raises(BasicError, match=r'IF sin cerrar \(linea fuente 251; falta END IF\)'):
        BasicSession(main_menu, libraries=[library])


def test_dragon_blank_input_chains_to_menu_and_menu_is_valid_when_closed(tmp_path):
    corpus = os.environ.get('BAS_CORPUS_ZIP')
    if not corpus or not Path(corpus).is_file():
        pytest.skip('Se requiere BAS_CORPUS_ZIP')
    with ZipFile(corpus) as archive:
        dragon = archive.read('graficos/dragon.bas').decode('latin1')
        menu = archive.read('menu.bas').decode('latin1')
        library = archive.read('utiles.bas').decode('latin1')
    # Reparacion solo de la copia TEMPORAL, nunca del archivo original.
    assert menu.count('        EndIf') >= 1 or '        EndIf' in menu
    menu = menu.replace('    EndIf\r\n  Loop\r\nEND SUB',
                        '    EndIf\r\n  EndIf\r\n  Loop\r\nEND SUB')
    # El menu valido se puede compilar con la biblioteca actual.
    BasicSession(menu, libraries=[library])
    sd_root = tmp_path / 'sd'
    target = sd_root / 'bas' / 'menu.bas'
    target.parent.mkdir(parents=True)
    target.write_text(menu, encoding='latin1')
    (sd_root / 'bas' / 'graficos').mkdir(parents=True)
    drives = VirtualDrives(b=sd_root)
    drives.chdir('B:/bas/graficos')
    session = BasicSession(dragon, drives=drives, libraries=[library])
    for _ in range(500):
        if session.step().state == 'waiting_input':
            break
    else:
        pytest.fail('Dragon no llego a su primer INPUT')
    session.input_value('2')
    for _ in range(10000):
        result = session.step()
        if result.state == 'waiting_input':
            break
    else:
        pytest.fail('Dragon no llego al INPUT posterior al dibujo')
    session.input_value('')
    for _ in range(500):
        session.step()
        if session.chain_count:
            break
    assert session.chain_count == 1
    assert session.active_path == target


def test_chain_error_names_destination(tmp_path):
    from basic_cde.core.expressions import BasicError
    sd_root = tmp_path / 'sd'
    (sd_root / 'bas').mkdir(parents=True)
    (sd_root / 'bas' / 'menu.bas').write_text('IF 1 THEN\nPRINT "BAD"', encoding='utf-8')
    drives = VirtualDrives(b=sd_root)
    session = BasicSession('RUN "B:/bas/menu.bas"', drives=drives)
    with pytest.raises(BasicError, match=r'Error en menu.bas \(RUN\): Bloque IF sin cerrar \(linea fuente 1; falta END IF\)'):
        session.step()
