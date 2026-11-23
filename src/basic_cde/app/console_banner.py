"""Banner de inicio de BASIC PicoCalc Emulator."""

import platform


def startup_lines(*, linux_version, loaded_program=None):
    system = platform.system()
    system_name = "macOS" if system == "Darwin" else system
    lines = [
        "BASIC PicoCalc Emulator V6.00.03",
        f"Ariel Palazzesi - {system_name} v{linux_version}",
    ]
    if loaded_program:
        lines.append(f"Cargado {loaded_program}")
    lines.append("READY")
    return lines
