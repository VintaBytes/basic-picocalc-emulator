"""LOG() natural del manual de PicoMite."""
import math
import pytest
from basic_cde.core.expressions import BasicError
from basic_cde.core.machine import BasicMachine


def test_log_natural():
    m = BasicMachine('PRINT LOG(1)\nPRINT LOG(2.718281828459045)\nEND')
    values = [float(x.strip()) for x in m.run().splitlines()]
    assert values[0] == pytest.approx(0)
    assert values[1] == pytest.approx(1)


def test_logarithm_ordinate_original_formula():
    m = BasicMachine('A=3 : B=5\nY0=LOG(B)/LOG(A)\nPRINT Y0\nEND')
    assert float(m.run().strip()) == pytest.approx(math.log(5)/math.log(3))


@pytest.mark.parametrize('argument', ['0', '-2'])
def test_log_domain_error(argument):
    with pytest.raises(BasicError, match='LOG'):
        BasicMachine(f'PRINT LOG({argument})').run()


def test_log_argument_count():
    with pytest.raises(BasicError, match='LOG'):
        BasicMachine('PRINT LOG(2,3)').run()


def test_original_logarithm_analysis_reaches_pause():
    import os
    from pathlib import Path
    from zipfile import ZipFile

    archive = os.environ.get('BAS_CORPUS_ZIP')
    if not archive or not Path(archive).is_file():
        pytest.skip('Configurar BAS_CORPUS_ZIP')
    with ZipFile(archive) as zipped:
        main = zipped.read('mate/log_0_info.bas').decode('utf-8-sig')
        library = zipped.read('utiles.bas').decode('utf-8-sig')

    machine = BasicMachine(main, libraries=[library])
    entries = iter(['3', '4', '5'])
    output = []
    for _ in range(3000):
        result = machine.step()
        output.append(result.output)
        if result.state == 'waiting_input':
            if 'PRESIONE' in result.prompt.upper():
                break
            machine.input_value(next(entries))
    else:
        pytest.fail('El programa no alcanzo la pausa tras calcular y(0)')

    result_text = ''.join(output)
    assert 'ORDENADA AL ORIGEN:' in result_text
    assert '1.464973' in result_text
    assert 'RAIZ (CORTE CON EJE X)' in result_text
