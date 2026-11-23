"""Regresiones del programa LUNAR, sin reescribir fuentes originales."""
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from basic_cde.app.session import BasicSession
from basic_cde.core.machine import BasicMachine
from basic_cde.core.expressions import BasicError
from basic_cde.devices.drives import VirtualDrives


def test_function_can_call_sub_that_prints():
    source = """PRINT SHOW%(5)
END
FUNCTION SHOW%(X)
  MESSAGE X
  SHOW% = X + 2
END FUNCTION
SUB MESSAGE(X)
  PRINT "NUM="; X
END SUB
"""
    assert BasicMachine(source).run() == 'NUM=5\n7\n'


def test_nested_functions_keep_output_in_execution_order():
    source = """PRINT OUTER%()
END
FUNCTION OUTER%()
  INNER
  OUTER% = 8
END FUNCTION
SUB INNER()
 PRINT "INTERIOR"
END SUB
"""
    assert BasicMachine(source).run() == 'INTERIOR\n8\n'


def test_timer_milliseconds_and_reset():
    now = [20.0]
    machine = BasicMachine('PRINT TIMER\nTIMER = 200\nPRINT TIMER\nEND', clock=lambda: now[0])
    now[0] += 1.5
    assert machine.value('TIMER') == 1500
    assert machine.step().output == '1500\n'
    machine.step()
    assert machine.value('TIMER') == 200
    now[0] += 0.125
    assert machine.value('TIMER') == 325
    assert machine.step().output == '325\n'


def test_timer_rejects_strings():
    with pytest.raises(BasicError, match='TIMER'):
        BasicMachine('TIMER = "hola"').run()


@pytest.mark.parametrize("numeric_input", ["0", ""] )
def test_original_lunar_reaches_endgame_and_chains(tmp_path, numeric_input):
    """Prueba de integración opcional: necesita ZIP original, nunca se modifica."""
    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Definir BAS_CORPUS_ZIP con la ruta al bas.zip original')
    with ZipFile(archive) as zipped:
        original = zipped.read('juegost/lunar_lander.bas').decode('utf-8-sig')
        library = zipped.read('utiles.bas').decode('utf-8-sig')
        menu = zipped.read('juegost/menu.bas')

    # B: representa la RAIZ de la SD; la carpeta 'bas' es hija.
    sd = tmp_path / 'sd'
    folder = sd / 'bas' / 'juegost'
    folder.mkdir(parents=True)
    (folder / 'menu.bas').write_bytes(menu)
    session = BasicSession(original, drives=VirtualDrives(b=sd), libraries=[library])
    session.machine.keyboard.push('xy')
    output = []
    for _ in range(10000):
        result = session.step()
        output.append(result.output)
        if result.state == 'waiting_input':
            session.input_value(numeric_input)
        if session.chain_count:
            break
    else:
        pytest.fail('LUNAR no alcanzo RUN menu.bas')
    rendered = ''.join(output)
    assert 'SIMULADOR DE ALUNIZAJES' in rendered
    assert 'NO HAY SOBREVIVIENTES' in rendered
    assert 'INTENTAS OTRA VEZ?' in rendered
    assert session.active_path == folder / 'menu.bas'
    assert session.machine.pc == 0
