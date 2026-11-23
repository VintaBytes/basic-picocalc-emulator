"""Comprobaciones de etiquetas del runner de corpus."""
import importlib.util
from pathlib import Path

script = Path(__file__).resolve().parents[1] / 'scripts' / 'regresion_corpus_bas.py'
spec = importlib.util.spec_from_file_location('regresion_corpus_bas', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_classify_success():
    assert module.classify(0, '', 'OK', False)[0] == 'TERMINA'


def test_classify_eof_input():
    assert module.classify(1, 'EOFError: EOF when reading a line', '', False)[0] == 'ESPERA_INPUT'


def test_classify_instruction_budget():
    assert module.classify(1, '? Limite configurado: 12000 instrucciones', '', False)[0] == 'LIMITE_INSTRUCCIONES'


def test_classify_timeout():
    assert module.classify(1, '', '', True)[0] == 'TIEMPO_AGOTADO'


def test_classify_bad_basic():
    assert module.classify(1, '? Instruccion no disponible: XXX', '', False)[0] == 'ERROR'
