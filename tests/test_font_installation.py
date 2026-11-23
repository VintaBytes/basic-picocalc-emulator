"""Instalacion offline de ROM originales a partir de archivos .h."""
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

from basic_cde.devices.rom_fonts import SOURCES, load_original_fonts
from test_rom_font_import import make_c_font


def test_install_from_local_font_headers(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    spec = spec_from_file_location('instalar_fuentes', root / 'scripts' / 'instalar_fuentes.py')
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    source = tmp_path / 'fuentes'
    source.mkdir()
    for number, name in SOURCES.items():
        (source / name).write_text(make_c_font(number), encoding='utf-8')
    target = tmp_path / 'instaladas'
    monkeypatch.setattr(mod, 'TARGET', target)
    mod.install(source)
    assert set(p.name for p in target.glob('*.h')) == set(SOURCES.values())
    parsed = load_original_fonts(target)
    assert len(parsed) == 8
    assert all(font.pixel(65, 0, 0) for font in parsed.values())
