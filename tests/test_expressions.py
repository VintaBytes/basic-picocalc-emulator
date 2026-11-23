import pytest
from basic_cde.core.expressions import BasicError, evaluate


def test_precedence():
    assert evaluate("2+3*4") == 14
    assert evaluate("2^3^2") == 512
    assert evaluate("(2+3)*4") == 20


def test_strings_and_vars():
    assert evaluate('"HOLA"+"!"') == "HOLA!"
    assert evaluate("A*2", {"A": 5}) == 10


def test_bitwise():
    assert evaluate("5 AND 3") == 1
    assert evaluate("5 XOR 3") == 6


def test_reject_code():
    with pytest.raises(BasicError):
        evaluate('__import__("os")')
