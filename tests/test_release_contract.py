"""Contrato del motor que necesita el consumidor grafico Qt."""
from basic_cde import __version__
from basic_cde.core.machine import BasicMachine, StepResult

def test_step_result_includes_graphics():
    assert __version__ == "0.3.10-dev"
    assert "graphics" in StepResult.__dataclass_fields__
    machine = BasicMachine('PIXEL 1,2,RGB(3,4,5)\nEND')
    result = machine.step()
    assert result.graphics == ("pixel", 1, 2, 0x030405)
