"""Sesión de programas encadenados y bibliotecas explícitas.

Las fuentes de las bibliotecas se adjuntan como declaraciones, sin escribir
ni modificar ninguno de los BAS montados.
"""
import shutil
import subprocess
import os
from pathlib import Path

from basic_cde.core.machine import BasicMachine, PersistentMemory
from basic_cde.core.expressions import BasicError
from basic_cde.devices.display import BitmapDisplay
from basic_cde.devices.raster_images import decode_image


class BasicSession:
    def __init__(self, source, *, drives=None, keyboard=None, clock=None,
                 libraries=(), max_chains=64, volume=70, persistent_path=None):
        self.drives = drives
        # GUI sessions retain the small reset marker separately from disk A:.
        # Callers can supply an isolated path in tests.
        if persistent_path is None:
            state_root = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
            persistent_path = state_root / 'basic-cde-linux' / 'persistent.json'
        self.persistent_store = PersistentMemory(persistent_path)
        self.keyboard = keyboard
        self.clock = clock
        self.libraries = tuple(libraries)
        self.max_chains = max_chains
        self.chain_count = 0
        self.active_path = None
        # Solo metadatos de diagnostico: no afectan el RUN ni las variables BASIC.
        self.chain_requested = None
        self.chain_target = None
        self._mod_player = None
        self.volume = max(0, min(100, int(volume)))
        self.display = BitmapDisplay()
        self.machine = self._new_machine(source)

    def _new_machine(self, source, *, cmdline="", preserved_machine=None):
        machine = BasicMachine(source, drives=self.drives, keyboard=self.keyboard,
                               clock=self.clock, libraries=self.libraries,
                               persistent_store=self.persistent_store,
                               cmdline=cmdline)
        if preserved_machine is not None:
            # CHAIN conserva variables, pero el nuevo programa comienza en su
            # primera instruccion con sus propias etiquetas y rutinas.
            machine.variables.globals.update({
                name: value for name, value in preserved_machine.variables.globals.items()
                if not name.startswith('MM.')
            })
            machine.option_base = preserved_machine.option_base
            machine.option_default = preserved_machine.option_default
            machine.variables.angle_degrees = preserved_machine.variables.angle_degrees
        return machine

    def step(self):
        self.chain_requested = None
        self.chain_target = None
        result = self.machine.step()
        if result.state != 'chain':
            if result.audio:
                self._audio_action(result.audio)
            if result.state == 'finished':
                self.stop_audio()
            # La pantalla de referencia se actualiza en el mismo orden que
            # las instrucciones BASIC, sin depender del hilo de eventos Qt.
            if result.graphics:
                if result.graphics[0] == 'sprite_load_file':
                    if self.drives is None:
                        raise BasicError('SPRITE LOAD requiere unidad montada')
                    from pathlib import Path
                    _, action, number, filename, *opts = result.graphics
                    suffix = '.png' if action == 'LOADPNG' else '.bmp'
                    path = self.drives.resolve(filename if Path(filename).suffix else filename + suffix)
                    if (not path.is_file() and self.active_path is not None
                            and '/' not in filename and '\\' not in filename and ':' not in filename):
                        candidate = (self.active_path.parent / path.name).resolve()
                        if any(root is not None and candidate.is_relative_to(root)
                               for root in self.drives.roots.values()):
                            path = candidate
                    if not path.is_file():
                        raise BasicError(f'SPRITE {action}: archivo inexistente: {filename}')
                    width,height,rgba = decode_image(path, 'PNG' if action == 'LOADPNG' else 'IMAGE')
                    if action == 'LOADBMP':
                        if len(opts) == 0:
                            x,y,w,h = 0,0,width,height
                        elif len(opts) == 2:
                            x,y = opts
                            w,h = width-x,height-y
                        else:
                            x,y,w,h = opts
                        if (x < 0 or y < 0 or w <= 0 or h <= 0 or
                                x+w > width or y+h > height):
                            raise BasicError('SPRITE LOADBMP: region invalida')
                        rgba = b''.join(rgba[((y+j)*width+x)*4:
                                             ((y+j)*width+x+w)*4] for j in range(h))
                        width,height = w,h
                        opts = []
                    graphic = ('sprite_load_data', action, number, width, height, rgba, *opts)
                    self.display.graphics(graphic)
                    return type(result)(result.state, output=result.output,
                                        prompt=result.prompt, graphics=graphic,
                                        next_program=result.next_program)
                if result.graphics[0] == 'blit_load_file':
                    if self.drives is None:
                        raise BasicError('BLIT LOAD requiere unidad montada')
                    _, number, filename, *region = result.graphics
                    from pathlib import Path
                    name = filename if Path(filename).suffix else filename + '.bmp'
                    path = self.drives.resolve(name)
                    if (not path.is_file() and self.active_path is not None
                            and '/' not in filename and '\\' not in filename and ':' not in filename):
                        candidate = (self.active_path.parent / path.name).resolve()
                        if any(root is not None and candidate.is_relative_to(root)
                               for root in self.drives.roots.values()):
                            path = candidate
                    if not path.is_file():
                        raise BasicError(f'BLIT LOAD: archivo inexistente: {filename}')
                    full_w, full_h, pixels = decode_image(path, 'IMAGE')
                    if len(region) == 0:
                        x, y, width, height = 0, 0, full_w, full_h
                    elif len(region) == 2:
                        x, y = region
                        width, height = full_w - x, full_h - y
                    else:
                        x, y, width, height = region
                    if (width <= 0 or height <= 0 or x < 0 or y < 0 or
                            x + width > full_w or y + height > full_h):
                        raise BasicError('BLIT LOAD: region fuera de imagen')
                    cropped = b''.join(pixels[((y + j) * full_w + x) * 4:
                                               ((y + j) * full_w + x + width) * 4]
                                       for j in range(height))
                    graphic = ('blit_load_data', number, x, y, width, height, cropped)
                    self.display.graphics(graphic)
                    return type(result)(result.state, output=result.output,
                                        prompt=result.prompt, graphics=graphic,
                                        next_program=result.next_program)
                if result.graphics[0] == 'load_raster':
                    if self.drives is None:
                        raise BasicError('LOAD JPG requiere unidad virtual montada')
                    _, fmt, name, x, y, *extra = result.graphics
                    suffix = {'JPG': '.jpg', 'PNG': '.png', 'IMAGE': '.bmp'}[fmt]
                    path = self.drives.resolve(name if __import__('pathlib').Path(name).suffix
                                               else name + suffix)
                    # El RUN encadenado por ruta absoluta puede no haber
                    # cambiado CWD: buscar junto al BAS solo como respaldo.
                    if (not path.is_file() and self.active_path is not None
                            and '/' not in name and '\\' not in name and ':' not in name):
                        candidate = (self.active_path.parent / path.name).resolve()
                        mounted = [root for root in self.drives.roots.values()
                                   if root is not None]
                        if any(candidate.is_relative_to(root) for root in mounted):
                            path = candidate
                    if not path.is_file():
                        raise BasicError(f'LOAD {fmt}: archivo inexistente: {name}')
                    width, height, rgba = decode_image(path, fmt)
                    if fmt == 'PNG':
                        from basic_cde.devices.raster_images import apply_png_transparency
                        rgba = apply_png_transparency(rgba, *extra)
                    graphic = ('load_raster', fmt, name, x, y, width, height, rgba)
                    self.display.graphics(graphic)
                    return type(result)(result.state, output=result.output,
                                        prompt=result.prompt, graphics=graphic,
                                        next_program=result.next_program)
                if result.graphics[0] == 'save_image':
                    if self.drives is None:
                        raise BasicError('SAVE IMAGE requiere una unidad montada')
                    self.drives.save_image(result.graphics[1], self.display.framebuffer)
                    return type(result)(result.state, output=result.output,
                                        prompt=result.prompt,
                                        next_program=result.next_program)
                self.display.graphics(result.graphics)
            if result.output:
                self.display.console(result.output)
            return result
        if self.chain_count >= self.max_chains:
            raise BasicError('Limite de programas encadenados')
        self.chain_requested = result.next_program
        self.chain_target = None
        source, path = self.drives.load_program(result.next_program)
        self.chain_target = path
        try:
            new_machine = self._new_machine(
                source, cmdline=result.cmdline,
                preserved_machine=self.machine if result.preserve_variables else None)
        except BasicError as exc:
            # Si el destino es invalido, el programa saliente sigue intacto.
            verb = 'CHAIN' if result.preserve_variables else 'RUN'
            raise BasicError(f'Error en {path.name} ({verb}): {exc}') from exc
        self.stop_audio()
        # Al cambiar de programa MMBasic cierra los canales abiertos.
        for stream in self.machine.file_handles.values():
            stream.close()
        self.machine.file_handles.clear()
        # Sustitucion atomica: si carga o compila falla, no cambia el programa.
        self.machine = new_machine
        self.active_path = path
        self.chain_count += 1
        return type(result)('running')

    def stop_audio(self):
        """Detiene un reproductor iniciado por esta sesion, sin matar otros."""
        player, self._mod_player = self._mod_player, None
        if player is not None and player.poll() is None:
            player.terminate()
            try:
                player.wait(timeout=1)
            except subprocess.TimeoutExpired:
                player.kill()
                player.wait(timeout=1)

    def _audio_action(self, action):
        if action[0] == 'stop':
            self.stop_audio()
            return
        if action[0] == 'tone':
            _, left, right, duration = action
            executable = shutil.which('ffplay')
            if executable is None:
                raise BasicError('PLAY TONE: falta ffplay (paquete ffmpeg)')
            self.stop_audio()
            # aevalsrc genera dos canales independientes. Los argumentos se
            # pasan sin shell; no hay archivos temporales ni espera bloqueante.
            def freq(value):
                return format(value, '.10g')
            source = (f'aevalsrc=exprs=sin(2*PI*{freq(left)}*t)|'
                      f'sin(2*PI*{freq(right)}*t):s=44100')
            if duration is not None:
                source += f':d={format(duration / 1000.0, ".10g")}'
            try:
                self._mod_player = subprocess.Popen(
                    [executable, '-nodisp', '-autoexit', '-loglevel', 'error',
                     '-volume', str(self.volume), '-f', 'lavfi', '-i', source],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as exc:
                raise BasicError(f'PLAY TONE: no se puede iniciar audio: {exc}') from exc
            return
        if action[0] != 'modfile':
            raise BasicError(f'Accion de audio no reconocida: {action[0]}')
        executable = shutil.which('ffplay')
        if executable is None:
            raise BasicError('PLAY MODFILE: falta ffplay (paquete ffmpeg)')
        self.stop_audio()
        # No shell: el archivo ya fue resuelto dentro de A:/B:.
        try:
            self._mod_player = subprocess.Popen(
                [executable, '-nodisp', '-autoexit', '-loglevel', 'error',
                 '-volume', str(self.volume), '-loop', '0', action[1]],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise BasicError(f'PLAY MODFILE: no se puede iniciar audio: {exc}') from exc

    def input_value(self, value):
        self.machine.input_value(value)

    @classmethod
    def with_library_files(cls, source, library_paths, **kwargs):
        texts = []
        for path in library_paths:
            try:
                texts.append(path.read_text(encoding='utf-8-sig'))
            except UnicodeDecodeError:
                texts.append(path.read_text(encoding='latin-1'))
        return cls(source, libraries=texts, **kwargs)
