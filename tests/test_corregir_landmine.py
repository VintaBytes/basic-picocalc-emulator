"""El generador de Landmine debe preservar el original y no sobrescribir."""
import pytest
from tools.corregir_landmine import corregir, CAMBIOS


def test_landmine_copy_only(tmp_path):
    source = tmp_path / "landmine.bas"
    target = tmp_path / "landmine_corregido.bas"
    lines = ["' original\r\n" for _ in range(561)]
    for number, (old, _) in CAMBIOS.items():
        lines[number - 1] = old + "\r\n"
    source.write_bytes("".join(lines).encode("latin-1"))
    original = source.read_bytes()
    assert corregir(source, target) == 17
    assert source.read_bytes() == original
    assert len(target.read_bytes().splitlines()) == 561
    with pytest.raises(FileExistsError):
        corregir(source, target)
    with pytest.raises(ValueError):
        corregir(source, source)


def test_landmine_wrong_source_is_not_modified(tmp_path):
    origin = tmp_path / "source.bas"
    target = tmp_path / "output.bas"
    origin.write_text("PRINT 1\n")
    with pytest.raises(ValueError):
        corregir(origin, target)
    assert not target.exists()
