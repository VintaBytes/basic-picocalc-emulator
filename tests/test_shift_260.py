import pytest

from basic_cde.core.expressions import evaluate, BasicError


def test_basic_shifts():
    assert evaluate("1<<3") == 8
    assert evaluate("128>>4") == 8
    assert evaluate("1<<0") == 1
    assert evaluate("1<<63") == -(1 << 63)
    assert evaluate("1<<63>>63") == 1


def test_board_expression():
    variables = {"XXSET": 0x80, "TMP": 7}
    assert evaluate("xxSet AND (1<<tmp)", variables) == 128
    variables["TMP"] = 6
    assert evaluate("xxSet AND (1<<tmp)", variables) == 0


def test_shift_precedence():
    assert evaluate("1+2<<3") == 24
    assert evaluate("1<<3=8") == 1
    assert evaluate("1<<3 AND 2") == 0


@pytest.mark.parametrize("text", ["1<<-1", "1>>64", "1<<1.5"])
def test_invalid_shift(text):
    with pytest.raises(BasicError):
        evaluate(text)
