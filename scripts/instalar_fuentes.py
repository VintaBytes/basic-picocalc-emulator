#!/usr/bin/env python3
"""Importa las ocho tablas bitmap PicoMite al paquete BASIC CDE Linux.

Opciones:
  python scripts/instalar_fuentes.py /ruta/a/cabeceras_originales
  python scripts/instalar_fuentes.py --descargar

La descarga usa SOLO los ocho archivos de fuentes publicadas; no descarga
ni incorpora el codigo del interprete MMBasic al proyecto.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from basic_cde.devices.rom_fonts import SOURCES, load_original_fonts  # noqa: E402

TARGET = ROOT / 'src' / 'basic_cde' / 'devices' / 'font_data'
# Pin the source revision audited in docs/THIRD_PARTY_NOTICES.md.
UPSTREAM_REVISION = '8adc11f3ba5e2a0a496363e732995ca1b009f697'
UPSTREAM = f'https://raw.githubusercontent.com/cuu/PicoMite/{UPSTREAM_REVISION}/'


def install(source: Path | None, *, download: bool = False) -> None:
    if not download:
        if source is None:
            raise ValueError('Indica directorio de fuentes originales o --descargar')
        # Valida las ocho tablas completas antes de copiar nada.
        originals = load_original_fonts(source)
        pending = {n: (source / name).read_bytes() for n, name in SOURCES.items()}
    else:
        # Acceso a red solo durante instalacion, nunca al ejecutar BASIC CDE.
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            temp = Path(tmp)
            for name in SOURCES.values():
                upstream_name = name.split('-', 1)[1]
                with urlopen(UPSTREAM + upstream_name, timeout=30) as response:
                    (temp / name).write_bytes(response.read())
            originals = load_original_fonts(temp)
            pending = {n: (temp / name).read_bytes() for n, name in SOURCES.items()}
    TARGET.mkdir(parents=True, exist_ok=True)
    for number, contents in pending.items():
        (TARGET / SOURCES[number]).write_bytes(contents)
    for number, font in originals.items():
        print(f'FONT {number}: {font.width}x{font.height}, '
              f'{font.count} glifos, desde CHR$({font.first})')
    print(f'Ocho fuentes instaladas en {TARGET}')


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == '--descargar':
        install(None, download=True)
    elif len(sys.argv) == 2:
        install(Path(sys.argv[1]))
    else:
        print('Uso: python scripts/instalar_fuentes.py '
              '<ruta/fuentes/originales> | --descargar', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
