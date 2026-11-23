#!/usr/bin/env python3
"""Explora graficos/*.bas del corpus original sin modificar los archivos.

Uso:
    python scripts/diagnosticar_graficos.py /ruta/a/bas.zip --steps 6000

'Avanza' significa que la demo supero su primer bloqueo y produjo una
salida visible. No equivale a verificar una ejecución completa o la GUI.
"""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from basic_cde.app.session import BasicSession
from basic_cde.devices.drives import VirtualDrives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path, help='ZIP de programas BAS de la SD')
    parser.add_argument('--steps', type=int, default=6000,
                        help='maximo de instrucciones por demo')
    args = parser.parse_args()
    if args.steps < 1:
        parser.error('--steps debe ser positivo')

    with ZipFile(args.corpus) as z, TemporaryDirectory(prefix='basic-cde-graphics-') as temp:
        sd = Path(temp)
        # Solo archivos de nombre conocido y contenido BAS; no descomprimir
        # rutas arbitrarias del ZIP ni tocar el sistema de archivos original.
        for name in z.namelist():
            p = Path(name)
            if (p.suffix.lower() != '.bas' or p.is_absolute() or
                    '..' in p.parts or any(':' in seg for seg in p.parts)):
                continue
            dest = sd.joinpath(*p.parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(name))
        library = z.read('utiles.bas').decode('latin1') if 'utiles.bas' in z.namelist() else ''
        for path in sorted((sd/'graficos').glob('*.bas')):
            count = drawings = 0
            try:
                drives = VirtualDrives(b=sd)
                session = BasicSession(path.read_text(encoding='latin1'),
                                       libraries=[library] if library else [], drives=drives)
                state = 'limite de pasos'
                for count in range(1, args.steps+1):
                    result = session.step()
                    drawings += bool(result.graphics)
                    if result.state in ('finished','waiting_input','waiting_time','chain'):
                        state = result.state
                        break
                status = f'{state}, graficos={drawings}'
            except Exception as exc:
                status = f'{type(exc).__name__}: {exc}'
            print(f'{path.name:23} {count:6}  {status}')


if __name__ == '__main__':
    main()
