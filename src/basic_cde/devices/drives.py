"""Unidades A:/B: montadas en carpetas locales, confinadas a sus raices.

No transforma rutas BASIC en rutas absolutas del host sin comprobarlas.
"""
from pathlib import Path
import re
import os
import tempfile
from basic_cde.core.expressions import BasicError


def detect_sd_root(folder):
    """Reconoce la estructura de SD habitual: sdcard/bas/...

    Si B: fue montada por error sobre bas/, devuelve su padre sdcard/.
    Solo corrige la estructura conocida: boot.bas + juegost/juegosg.
    No modifica el contenido de los archivos.
    """
    candidate = Path(folder).expanduser().resolve(strict=True)
    if (candidate.name.casefold() == 'bas'
            and (candidate / 'boot.bas').is_file()
            and (candidate / 'juegosg').is_dir()
            and (candidate / 'juegost').is_dir()
            and (candidate.parent / 'bas').resolve() == candidate):
        return candidate.parent
    return candidate


class VirtualDrives:
    def __init__(self, a=None, b=None):
        self.roots = {'A': None, 'B': None}
        self.cwd = {'A': (), 'B': ()}
        self.current = 'A'
        if a is not None:
            self.mount('A', a)
        if b is not None:
            self.mount('B', b)

    def mount(self, drive, root):
        drive = self._drive(drive)
        path = Path(root).expanduser().resolve(strict=True)
        if not path.is_dir():
            raise BasicError(f'No es carpeta: {path}')
        self.roots[drive] = path
        self.cwd[drive] = ()

    @staticmethod
    def _drive(value):
        value = str(value).upper().rstrip(':')
        if value not in ('A', 'B'):
            raise BasicError(f'Unidad desconocida: {value}')
        return value

    def drive(self, value):
        drive = self._drive(value)
        if self.roots[drive] is None:
            raise BasicError(f'Unidad {drive}: sin montar')
        self.current = drive

    def _parts(self, filename):
        text = str(filename).replace('\\', '/')
        match = re.match(r'^([ABab]):(.*)$', text)
        if match:
            drive = match.group(1).upper()
            raw = match.group(2)
            if not raw.startswith('/'):
                raise BasicError('Ruta con unidad debe comenzar en la raiz')
            parts = []
        else:
            drive = self.current
            parts = [] if text.startswith('/') else list(self.cwd[drive])
            raw = text
        if self.roots[drive] is None:
            raise BasicError(f'Unidad {drive}: sin montar')
        for segment in raw.split('/'):
            if segment in ('', '.'):
                continue
            if segment == '..':
                if not parts:
                    raise BasicError('Ruta fuera de unidad virtual')
                parts.pop()
            else:
                if '\x00' in segment or ':' in segment:
                    raise BasicError('Nombre de archivo no valido')
                parts.append(segment)
        return drive, parts

    def resolve(self, filename, *, directory=False):
        drive, parts = self._parts(filename)
        root = self.roots[drive]
        path = root
        for segment in parts:
            if drive == 'B':
                try:
                    matches = [p for p in path.iterdir() if p.name.casefold() == segment.casefold()]
                except (OSError, NotADirectoryError):
                    matches = []
                if matches:
                    if len(matches) > 1:
                        raise BasicError(f'Nombre ambiguo en B: {segment}')
                    segment = matches[0].name
            path = path / segment
            # Resolve each component; this also checks symlink escapes.
            candidate = path.resolve(strict=False)
            if not candidate.is_relative_to(root):
                raise BasicError('Acceso fuera de la unidad virtual')
        candidate = path.resolve(strict=False)
        if not candidate.is_relative_to(root):
            raise BasicError('Acceso fuera de la unidad virtual')
        if directory and not candidate.is_dir():
            raise BasicError(f'Directorio inexistente: {filename}')
        return candidate

    def chdir(self, filename):
        drive, _ = self._parts(filename)
        path = self.resolve(filename, directory=True)
        self.current = drive
        self.cwd[drive] = path.relative_to(self.roots[drive]).parts

    @property
    def cwd_string(self):
        suffix = '/'.join(self.cwd[self.current])
        return f'{self.current}:/' + suffix

    def load_program(self, filename):
        name = str(filename)
        if not Path(name).suffix:
            name += '.bas'
        path = self.resolve(name)
        if not path.is_file():
            raise BasicError(f'Archivo BAS inexistente: {filename}')
        try:
            return path.read_text(encoding='utf-8-sig'), path
        except UnicodeDecodeError:
            # El corpus incluye una fuente no UTF-8; mantener los bytes en disco.
            return path.read_text(encoding='latin-1'), path
        except OSError as exc:
            raise BasicError(f'No se pudo leer {filename}: {exc}') from exc

    def save_program(self, filename, source):
        """Guarda el fuente BASIC en A:/B: de forma atomica.

        El comando SAVE reemplaza un BAS existente, como hace MMBasic.
        Nunca crea carpetas; la ruta se valida antes de escribir y el
        reemplazo temporal protege al fichero anterior si falla el guardado.
        """
        name = str(filename)
        if not Path(name).suffix:
            name += '.bas'
        path = self.resolve(name)
        if path.suffix.casefold() != '.bas':
            raise BasicError('SAVE solo admite archivos .bas')
        if not path.parent.is_dir():
            raise BasicError(f'Directorio inexistente: {filename}')
        if path.exists() and not path.is_file():
            raise BasicError(f'Destino no es archivo: {filename}')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                             prefix='.basic-cde-', suffix='.tmp',
                                             dir=path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(source)
            os.replace(temporary, path)
        except (OSError, UnicodeError) as exc:
            raise BasicError(f'SAVE: error al guardar {filename}: {exc}') from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path

    def save_image(self, filename, framebuffer):
        """Guarda un BMP dentro de la unidad virtual actual, atomicamente.

        La ruta se valida antes de escribir. Requiere carpeta de destino
        existente y nunca crea directorios fuera de las raices montadas.
        """
        name = str(filename)
        if not Path(name).suffix:
            name += '.bmp'
        if Path(name).suffix.lower() != '.bmp':
            raise BasicError('SAVE IMAGE solo admite archivos BMP')
        path = self.resolve(name)
        if not path.parent.is_dir():
            raise BasicError(f'Directorio inexistente: {filename}')
        if path.exists() and not path.is_file():
            raise BasicError(f'Destino no es archivo: {filename}')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix='.basic-cde-', suffix='.tmp',
                                             dir=path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(framebuffer.to_bmp())
            os.replace(temporary, path)
        except OSError as exc:
            raise BasicError(f'SAVE IMAGE: error al guardar {filename}: {exc}') from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path


    def kill(self, filename):
        """KILL file$: borra un solo archivo dentro de A:/B:.

        No se admite wildcard en esta fase: es preferible un error explícito
        a borrar por accidente un conjunto de ficheros del host.
        """
        name = str(filename)
        if not name or any(ch in name for ch in '*?'):
            raise BasicError('KILL: nombre o comodin no admitido')
        path = self.resolve(name)
        if not path.is_file():
            raise BasicError(f'KILL: archivo inexistente: {name}')
        try:
            path.unlink()
        except OSError as exc:
            raise BasicError(f'KILL: {exc}') from exc

    def rename(self, source, destination):
        """RENAME original$ AS nuevo$: renombrado en la misma unidad."""
        src, dst = str(source), str(destination)
        if not src or not dst or any(ch in item for item in (src, dst) for ch in '*?'):
            raise BasicError('RENAME: nombres invalidos')
        unit_src, _ = self._parts(src)
        unit_dst, _ = self._parts(dst)
        if unit_src != unit_dst:
            raise BasicError('RENAME: no admite unidades diferentes')
        old, new = self.resolve(src), self.resolve(dst)
        if not old.is_file():
            raise BasicError(f'RENAME: archivo inexistente: {src}')
        if new.exists():
            raise BasicError(f'RENAME: destino existente: {dst}')
        if not new.parent.is_dir():
            raise BasicError(f'RENAME: directorio inexistente: {dst}')
        try:
            old.rename(new)
        except OSError as exc:
            raise BasicError(f'RENAME: {exc}') from exc

    def copy(self, source, destination):
        """COPY origen$ TO destino$: copia regular, sin sobrescritura silenciosa."""
        import shutil
        src, dst = str(source), str(destination)
        if not src or not dst or any(ch in item for item in (src, dst) for ch in '*?'):
            raise BasicError('COPY: nombres invalidos')
        old, new = self.resolve(src), self.resolve(dst)
        if not old.is_file():
            raise BasicError(f'COPY: archivo inexistente: {src}')
        if new.exists():
            raise BasicError(f'COPY: destino existente: {dst}')
        if not new.parent.is_dir():
            raise BasicError(f'COPY: directorio inexistente: {dst}')
        try:
            # O_EXCL evita sobrescribir si aparece destino entre validación y escritura.
            with old.open('rb') as inp, new.open('xb') as out:
                shutil.copyfileobj(inp, out)
        except OSError as exc:
            raise BasicError(f'COPY: {exc}') from exc

    def mkdir(self, dirname):
        path = self.resolve(dirname)
        if not path.parent.is_dir() or path.exists():
            raise BasicError(f'MKDIR: directorio invalido o existente: {dirname}')
        try:
            path.mkdir()
        except OSError as exc:
            raise BasicError(f'MKDIR: {exc}') from exc

    def rmdir(self, dirname):
        path = self.resolve(dirname, directory=True)
        if path in [r for r in self.roots.values() if r is not None]:
            raise BasicError('RMDIR: no se puede eliminar raiz')
        if path == self.resolve(self.cwd_string):
            raise BasicError('RMDIR: no se puede eliminar directorio actual')
        try:
            path.rmdir()  # Solo directorios vacíos; nunca recursivo.
        except OSError as exc:
            raise BasicError(f'RMDIR: {exc}') from exc
