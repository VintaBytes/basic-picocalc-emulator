"""Listado FILES de la unidad virtual activa (sin tocar archivos externos)."""
from __future__ import annotations

from datetime import datetime
import shutil


def files_listing(drives) -> str:
    """Nombres, fechas, tamaños y espacio de la carpeta vinculada.

    El espacio libre es el del sistema de archivos anfitrion, no la
    capacidad de flash fisica de PicoCalc. No inventar un numero de bytes.
    """
    directory = drives.resolve('.', directory=True)
    entries = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.casefold()))
    lines = [drives.cwd_string, '    <DIR> .', '    <DIR> ..']
    dir_count = 2
    file_count = 0
    for entry in entries:
        # No seguir enlaces que salgan de los montajes virtuales.
        if entry.is_symlink():
            continue
        if entry.is_dir():
            dir_count += 1
            lines.append(f'    <DIR> {entry.name}')
        elif entry.is_file():
            file_count += 1
            stat = entry.stat()
            stamp = datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M %d-%m-%Y')
            lines.append(f'{stamp} {stat.st_size:>9} {entry.name}')
    free_bytes = shutil.disk_usage(directory).free
    lines.append(f'{dir_count} directories, {file_count} files, {free_bytes} bytes free')
    return '\n'.join(lines) + '\n'
