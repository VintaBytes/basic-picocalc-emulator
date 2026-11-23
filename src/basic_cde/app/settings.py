"""Preferencias locales de la aplicación (sin dependencia de Qt).

Los montajes se recuerdan en la configuración XDG del usuario, fuera de
la carpeta de instalación. No se guardan contenidos ni copias de la SD.
"""

import json
import os
from pathlib import Path
import tempfile


class MountSettings:
    """Guarda montajes y bibliotecas sin acoplamiento a Qt.

    El formato version 1 sigue siendo compatible con configuraciones previas.
    """

    def __init__(self, path=None):
        if path is None:
            base = os.environ.get('XDG_CONFIG_HOME')
            config_root = Path(base).expanduser() if base else Path.home() / '.config'
            path = config_root / 'basic-cde-linux' / 'settings.json'
        self.path = Path(path)

    def _read_data(self):
        """Lee preferencias validas; tolera configuraciones antiguas o dañadas."""
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (FileNotFoundError, OSError, UnicodeError, ValueError):
            return {}
        if not isinstance(data, dict) or data.get('version') != 1:
            return {}
        return data

    def load(self):
        """API histórica: devuelve solo montajes A: y B:."""
        mounts = self._read_data().get('mounts')
        if not isinstance(mounts, dict):
            return {}
        return {key: value for key in ('A', 'B')
                if isinstance(value := mounts.get(key), str) and value}

    def load_libraries(self):
        """Retorna rutas guardadas, sin abrir ni ejecutar archivos."""
        libraries = self._read_data().get('libraries', [])
        if not isinstance(libraries, list):
            return []
        return list(dict.fromkeys(path for path in libraries
                                  if isinstance(path, str) and path.strip()))

    def load_last_program(self):
        """Devuelve la ruta del ultimo BAS abierto, o None."""
        value = self._read_data().get('last_program')
        return value if isinstance(value, str) and value.strip() else None

    def load_function_keys(self):
        """Opciones de teclas persistentes sin contaminar la memoria BASIC."""
        from basic_cde.app.function_keys import CUSTOM_KEYS
        raw = self._read_data().get('function_keys')
        if not isinstance(raw, dict):
            return {}
        return {int(k): v for k, v in raw.items()
                if k.isdecimal() and int(k) in CUSTOM_KEYS and isinstance(v, str)}

    def load_volume(self) -> int:
        """Volumen privado de la aplicacion, 0..100 (por defecto 70)."""
        value = self._read_data().get('volume', 70)
        if isinstance(value, bool) or not isinstance(value, int):
            return 70
        return max(0, min(100, value))

    def load_language(self) -> str:
        """Idioma de la interfaz: es o en. Español por defecto."""
        value = self._read_data().get('language', 'es')
        return value if value in ('es', 'en') else 'es'

    def save_language(self, language: str):
        """Guarda el idioma preservando las demás preferencias."""
        if language not in ('es', 'en'):
            raise ValueError(f'Idioma no admitido: {language!r}')
        self._write(self.load(), self.load_libraries(),
                    self.load_last_program(), language=language)

    def save_volume(self, value: int):
        """Persiste el volumen sin perder montajes, programa ni teclas."""
        value = max(0, min(100, int(value)))
        self._write(self.load(), self.load_libraries(), self.load_last_program(),
                    volume=value)

    def save_function_keys(self, mappings):
        """Preserva unidades, bibliotecas y último programa al guardar."""
        from basic_cde.app.function_keys import CUSTOM_KEYS
        clean = {str(key): value for key, value in mappings.items()
                 if key in CUSTOM_KEYS and isinstance(value, str)}
        self._write(self.load(), self.load_libraries(), self.load_last_program(),
                    function_keys=clean)

    def save_last_program(self, path):
        """Persiste solo la ruta, sin copiar el contenido del programa."""
        self._write(self.load(), self.load_libraries(), str(path) if path else None)

    def save(self, mounts):
        """Actualiza montajes sin perder bibliotecas ni ultimo programa."""
        self._write(mounts, self.load_libraries(), self.load_last_program())

    def save_libraries(self, libraries):
        """Actualiza bibliotecas sin modificar los otros ajustes."""
        self._write(self.load(), libraries, self.load_last_program())

    def _write(self, mounts, libraries, last_program=None, function_keys=None,
               volume=None, language=None):
        """Escritura atomica, con permisos privados y listas deduplicadas."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {'version': 1, 'mounts': {
            key: str(value) for key in ('A', 'B')
            if (value := mounts.get(key)) is not None
        }, 'libraries': list(dict.fromkeys(str(p) for p in libraries if str(p).strip()))}
        if last_program:
            payload['last_program'] = str(last_program)
        payload['volume'] = self.load_volume() if volume is None else max(0, min(100, int(volume)))
        payload['language'] = self.load_language() if language is None else language
        payload['function_keys'] = (function_keys if function_keys is not None
                                    else {str(k): v for k, v in self.load_function_keys().items()})
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8',
                                             dir=self.path.parent,
                                             prefix='.settings-', suffix='.tmp',
                                             delete=False) as stream:
                temp_name = stream.name
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, self.path)
        finally:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)
