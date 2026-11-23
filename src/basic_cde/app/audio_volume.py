"""Control privado del flujo de audio de ffplay de BASIC CDE.

El volumen no modifica la salida maestra del sistema. Las preferencias se
persisten aparte; los cambios en vivo precisan pactl y un servidor PulseAudio
o PipeWire con compatibilidad Pulse. Evitar modificar otros flujos de audio.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess


def _sink_for_pid(listing: str, pid: int) -> str | None:
    """Extrae exclusivamente la entrada asociada al PID del ffplay propio."""
    try:
        payload = json.loads(listing)
        if isinstance(payload, list):
            for item in payload:
                props = item.get('properties', {})
                if str(props.get('application.process.id', '')) == str(pid):
                    return str(item['index'])
    except (ValueError, TypeError, KeyError, AttributeError):
        pass

    # Salida humana de pactl; válida si la versión no soporta JSON.
    for block in re.split(r'(?=^Sink Input #)', listing, flags=re.M):
        entry = re.search(r'^Sink Input #(\d+)', block, re.M)
        owner = re.search(r'application\.process\.id\s*=\s*"?(\d+)"?', block)
        if entry and owner and int(owner.group(1)) == int(pid):
            return entry.group(1)
    return None


def set_player_volume(pid: int, volume: int) -> bool:
    """Aplica 0..100 al stream activo; False si no se puede identificar."""
    if not pid or shutil.which('pactl') is None:
        return False
    volume = max(0, min(100, int(volume)))
    for listing_args in (['pactl', '-f', 'json', 'list', 'sink-inputs'],
                         ['pactl', 'list', 'sink-inputs']):
        try:
            listing = subprocess.run(listing_args, capture_output=True,
                                     text=True, timeout=1.5, check=True)
        except (OSError, subprocess.SubprocessError):
            continue
        sink = _sink_for_pid(listing.stdout, int(pid))
        if sink is None:
            continue
        try:
            subprocess.run(['pactl', 'set-sink-input-volume', sink,
                            f'{volume}%'], capture_output=True,
                           timeout=1.5, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            return False
    return False
