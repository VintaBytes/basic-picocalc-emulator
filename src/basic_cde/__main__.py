"""Punto de entrada: CLI headless o GUI PySide6."""
import argparse
import sys
from pathlib import Path
from .core.expressions import BasicError
from .app.session import BasicSession
from .devices.drives import VirtualDrives


def main():
    from . import __version__
    parser = argparse.ArgumentParser(description=f"BASIC PicoCalc Emulator {__version__}")
    parser.add_argument("program", nargs="?", help="Ruta al programa BAS")
    parser.add_argument('--mount-a', help='Carpeta local que representa A:')
    parser.add_argument('--mount-b', help='Carpeta local que representa B: (raiz SD)')
    parser.add_argument('--library', action='append', default=[], help='Biblioteca BAS adjunta (repetible)')
    parser.add_argument("--gui", action="store_true", help="Abrir ventana Qt")
    parser.add_argument("--max-instructions", type=int, default=None,
                        help="Limite opcional de instrucciones en CLI (sin limite por defecto)")
    args = parser.parse_args()
    if args.gui or not args.program:
        try:
            from .gui.window import launch
        except ImportError as exc:
            parser.error(f"PySide6 no esta instalado: {exc}")
        return launch(args.program, mount_a=args.mount_a, mount_b=args.mount_b, libraries=args.library)
    try:
        source = Path(args.program).read_text(encoding="utf-8-sig")
        drives = VirtualDrives(a=args.mount_a, b=args.mount_b)
        session = BasicSession.with_library_files(source, [Path(p) for p in args.library], drives=drives)
        diagnosed_machine = session.machine
        for warning in diagnosed_machine.warnings:
            print(warning, file=sys.stderr)
        count = 0
        while True:
            if args.max_instructions is not None and count >= args.max_instructions:
                raise BasicError(f'Limite configurado: {args.max_instructions} instrucciones')
            result = session.step()
            if session.machine is not diagnosed_machine:
                diagnosed_machine = session.machine
                for warning in diagnosed_machine.warnings:
                    print(warning, file=sys.stderr)
            count += 1
            if result.output:
                sys.stdout.write(result.output)
                sys.stdout.flush()
            if result.state == "finished":
                break
            if result.state == 'waiting_time':
                import time
                time.sleep(0.005)
            if result.state == "waiting_input":
                session.input_value(input(result.prompt))
    except (BasicError, UnicodeError, OSError) as exc:
        print(f"? {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
