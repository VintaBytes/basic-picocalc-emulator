"""Terminal READY independiente de Qt.

Conserva el texto del programa como documento editable y no lo ejecuta ni
lo escribe en disco hasta recibir una orden explicita. Los comandos BASIC
de ejecucion siguen pasando por el mismo BasicSession que usa la GUI.
"""
import re
from dataclasses import dataclass

from basic_cde.app.function_keys import parse_option_fn


class DirectCommandError(ValueError):
    pass


@dataclass(frozen=True)
class DirectResult:
    message: str = ''
    action: str = ''
    argument: str = ''
    modified: bool = False


class DirectConsole:
    """Edicion por numero de linea y comandos READY basicos.

    No confundir las ordenes directas con sentencias BASIC ejecutadas dentro
    de un programa. Mantener aqui una superficie pequena y comprobable.
    """
    def __init__(self, source=''):
        self.source = source

    def execute(self, text):
        text = text.strip()
        if not text:
            return DirectResult()
        numbered = re.fullmatch(r'(\d+)(?:\s+(.*))?', text, re.S)
        if numbered:
            line = int(numbered.group(1))
            if line > 65535:
                raise DirectCommandError('Numero de linea fuera de rango')
            body = numbered.group(2) or ''
            lines = self.source.splitlines()
            result = []
            inserted = False
            for old in lines:
                match = re.match(r'^\s*(\d+)(?:\s|$)', old)
                if match and int(match.group(1)) == line:
                    continue
                if not inserted and match and int(match.group(1)) > line:
                    if body:
                        result.append(f'{line} {body}')
                    inserted = True
                result.append(old)
            if not inserted and body:
                result.append(f'{line} {body}')
            self.source = '\n'.join(result) + ('\n' if result else '')
            return DirectResult(modified=True)
        # En READY A: y B: seleccionan la unidad virtual directamente.
        if re.fullmatch(r'[ABab]:', text):
            return DirectResult(action='drive', argument=text.upper())
        # '?' es la abreviatura clasica de PRINT; una asignacion no tiene
        # por que contener un espacio antes del signo '='.
        if text.startswith('?'):
            return DirectResult(action='immediate', argument=text)
        if re.fullmatch(r'[A-Za-z_][\w]*[$%!]?(?:\s*\([^\n]*\))?\s*=\s*.+', text):
            return DirectResult(action='immediate', argument=text)
        match = re.fullmatch(r'([A-Za-z]+)(?:\s+(.*))?', text, re.S)
        if not match:
            raise DirectCommandError('Comando directo no disponible')
        command = match.group(1).upper()
        arg = (match.group(2) or '').strip()
        if command == 'OPTION' and re.match(r'^F\d+(?:\s|$)', arg, re.I):
            number, value = parse_option_fn(text)
            return DirectResult(action='option_function_key', argument=f'{number}\x00{value}')
        if command == 'OPTION' and arg.upper() == 'LIST':
            return DirectResult(action='option_list')
        if command == 'MEMORY':
            if arg:
                raise DirectCommandError('MEMORY no admite argumentos en READY')
            return DirectResult(action='memory')
        if command == 'DRIVE':
            if not re.fullmatch(r'\"?[ABab]:\"?', arg):
                raise DirectCommandError('DRIVE: se esperaba A: o B:')
            return DirectResult(action='drive', argument=arg.strip('\"').upper())
        if command == 'CHDIR':
            if not arg:
                raise DirectCommandError('CHDIR: falta el directorio')
            return DirectResult(action='chdir', argument=self._filename(arg))
        if command == 'FILES':
            if arg:
                raise DirectCommandError('FILES no admite argumentos en esta version')
            return DirectResult(action='files')
        if command == 'LIST':
            bounds = re.fullmatch(r'(\d+)?\s*(?:-\s*(\d+)?)?', arg) if arg else None
            if arg and not bounds:
                raise DirectCommandError('LIST: rango invalido')
            lo = int(bounds.group(1)) if bounds and bounds.group(1) else 0
            hi = int(bounds.group(2)) if bounds and bounds.group(2) else 65535
            if hi < lo:
                raise DirectCommandError('LIST: rango invalido')
            lines = self.source.splitlines()
            if arg:
                lines = [line for line in lines if (m := re.match(r'^\s*(\d+)\b', line))
                         and lo <= int(m.group(1)) <= hi]
            return DirectResult(''.join(line + '\n' for line in lines))
        # La consola reconoce los nombres, pero todas las expresiones se
        # ejecutan en BasicMachine y no se reinterpretan aqui.
        if command in ('PRINT', 'CLS', 'COLOR', 'COLOUR', 'FONT', 'TEXT',
                       'PIXEL', 'LINE', 'BOX', 'CIRCLE', 'FRAMEBUFFER', 'LET', 'DIM',
                       'RANDOMIZE'):
            return DirectResult(action='immediate', argument=text)
        if command == 'EDIT':
            if arg:
                raise DirectCommandError('EDIT no admite argumentos')
            return DirectResult(action='edit')
        if command == 'NEW':
            if arg:
                raise DirectCommandError('NEW no admite argumentos')
            self.source = ''
            return DirectResult(action='new', modified=True)
        if command == 'RUN':
            if arg:
                return DirectResult(action='run_file', argument=self._filename(arg))
            if not self.source.strip():
                raise DirectCommandError('No hay programa cargado')
            return DirectResult(action='run')
        if command == 'LOAD':
            return DirectResult(action='load', argument=self._filename(arg))
        if command == 'SAVE':
            if not self.source.strip():
                raise DirectCommandError('No hay programa para guardar')
            return DirectResult(action='save', argument=self._filename(arg))
        if command == 'HELP' and not arg:
            return DirectResult('LIST [inicio-fin], RUN, LOAD "archivo.bas", SAVE "archivo.bas", NEW, EDIT\n'
                                'CLS, PRINT, ? , LET, DIM, COLOR, FONT y graficos\n'
                                'OPTION F1/F5..F9 expresion$, OPTION LIST, MEMORY, FILES\n'
                                'Escribi un numero de linea para editar el programa.\n')
        raise DirectCommandError(f'Comando directo no disponible: {command}')

    @staticmethod
    def _filename(arg):
        if len(arg) >= 2 and arg[0] == arg[-1] == '"':
            return arg[1:-1]
        raise DirectCommandError('Se esperaba un nombre de archivo entre comillas')


class DirectExecutor:
    """Ejecuta una sentencia de READY reutilizando BasicMachine.

    El estado de variables globales y los colores se preserva entre comandos
    directos. No se cambia la memoria del programa LIST/RUN: esto representa
    un espacio interactivo de ejecución, independiente de su texto fuente.
    Por seguridad no se aceptan bucles, saltos ni INPUT desde esta primera
    versión. Las sentencias autorizadas son evaluadas por el núcleo real.
    """
    def __init__(self, *, drives=None):
        from basic_cde.core.machine import BasicMachine
        self.drives = drives
        self.context = BasicMachine('', drives=drives)

    def reset(self):
        from basic_cde.core.machine import BasicMachine
        self.context = BasicMachine('', drives=self.drives)

    def execute(self, statement):
        from basic_cde.core.machine import BasicMachine
        from basic_cde.core.expressions import BasicError
        machine = BasicMachine(statement, drives=self.drives)
        # Reusar variables y generador aleatorio mantiene A=2 / PRINT A+1
        # entre comandos, pero no ejecuta nunca el programa LIST.
        machine.variables = self.context.variables
        machine.rng = self.context.rng
        machine.foreground = self.context.foreground
        machine.background = self.context.background
        machine.option_base = self.context.option_base
        results = []
        for _ in range(64):
            result = machine.step()
            if result.state == 'finished':
                self.context.foreground = machine.foreground
                self.context.background = machine.background
                self.context.option_base = machine.option_base
                return results
            if result.state != 'running':
                raise BasicError(f'Sentencia directa requiere RUN: {statement}')
            results.append(result)
        raise BasicError('Sentencia directa demasiado larga')
