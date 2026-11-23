"""RND sin parentesis, como en PicoCalc y demo.bas."""
import math
import random

from basic_cde.core.expressions import ExpressionParser
from basic_cde.app.session import BasicSession


def test_bare_rnd_advances_rng():
    rng = random.Random(123)
    expected = random.Random(123)
    first = ExpressionParser("RND", {}, rng).parse()
    second = ExpressionParser("RND()", {}, rng).parse()
    assert first == expected.random()
    assert second == expected.random()


def test_bare_rnd_in_log_and_compound_expression():
    x = ExpressionParser("-LOG(RND)", {}, random.Random(123)).parse()
    assert x == -math.log(random.Random(123).random())
    assert x > 0
    y = ExpressionParser("1+RND*2", {}, random.Random(123)).parse()
    assert y == 1+2*random.Random(123).random()


def test_demo_deep_line_211():
    session = BasicSession("S=-LOG(RND): T=1\nPRINT S\n")
    results=[]
    for _ in range(10):
        step=session.step()
        results.append(step.output)
        if step.state == "finished":
            break
        assert step.state == "running", step
    number=float(''.join(results).strip())
    assert number >= 0
