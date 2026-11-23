"""Interprete BASIC independiente de Qt con ejecucion cooperativa.

Las instrucciones no soportadas producen errores explicitos. Las rutinas
pueden suspenderse durante INPUT/PAUSE sin bloquear el hilo de interfaz.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import MutableMapping
import random
import math
import fnmatch
import shutil
import re
import time
import json
import os
import tempfile
from collections import deque
from threading import Lock
from pathlib import Path
from .expressions import BasicError, evaluate
from .longstrings import command as longstring_command, contents as longstring_contents, as_text as longstring_as_text


@dataclass(frozen=True)
class StepResult:
    state: str
    output: str = ""
    prompt: str = ""
    next_program: str = ""
    graphics: tuple = ()
    audio: tuple = ()
    cmdline: str = ""
    preserve_variables: bool = False


def _strip_comment(line):
    """Ignora apóstrofes fuera de cadenas, pero conserva comillas dobles."""
    quoted = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if quoted and i + 1 < len(line) and line[i + 1] == '"':
                i += 2
                continue
            quoted = not quoted
        if ch == "'" and not quoted:
            return line[:i]
        i += 1
    return line


def _split(text, separators=":"):
    """Separación respetando comillas y anidamiento de paréntesis."""
    result, current, quoted, nesting = [], [], False, 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            if quoted and i+1 < len(text) and text[i+1] == '"':
                current.extend(['"','"'])
                i += 2
                continue
            quoted = not quoted
        if not quoted:
            if ch == '(': nesting += 1
            if ch == ')': nesting -= 1
            if ch in separators and nesting == 0:
                result.append(''.join(current).strip())
                current = []
                i += 1
                continue
        current.append(ch)
        i += 1
    result.append(''.join(current).strip())
    return result




def _split_graphic_args(text):
    """Divide argumentos de graficos como el scanner MMBasic 6.00.03.

    'evaluate' en MMBasic.c permite que una expresion termine ante ')'.
    En un comando con argumentos separados por coma, un cierre aislado
    despues de una expresion no forma parte del siguiente argumento.
    Solo se omiten cierres excedentes en limites de argumentos; se
    conservan cierres correctos, comillas y sintaxis restante.
    Devuelve (campos, cantidad_de_cierres_aislados).
    """
    cleaned = []
    quoted = False
    depth = 0
    extra = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            if quoted and i + 1 < len(text) and text[i + 1] == '"':
                cleaned.extend(['"', '"'])
                i += 2
                continue
            quoted = not quoted
        if not quoted:
            if ch == '(':
                depth += 1
            elif ch == ')':
                if depth > 0:
                    depth -= 1
                elif text[i + 1:].lstrip().startswith(',') or not text[i + 1:].strip():
                    extra += 1
                    i += 1
                    continue
        cleaned.append(ch)
        i += 1
    return _split(''.join(cleaned), ','), extra


def _parse_print_at(text):
    """Lee PRINT @(x,y[,modo]) con expresiones anidadas.

    Un regex `[^()]*` rechaza casos legales como @(132,72+(i+2)*12,2).
    Devuelve (argumentos, texto_restante) o None si no empieza con @(. 
    """
    if not text.startswith('@('):
        return None
    depth = 1
    quoted = False
    i = 2
    while i < len(text):
        ch = text[i]
        if ch == '"':
            if quoted and i + 1 < len(text) and text[i + 1] == '"':
                i += 2
                continue
            quoted = not quoted
        elif not quoted:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return text[2:i], text[i + 1:].strip()
        i += 1
    raise BasicError('PRINT @: falta parentesis de cierre')


def _split_inline_else(text):
    """Separa ELSE de IF en una linea solo fuera de comillas/parentesis."""
    quoted, nesting = False, 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            if quoted and i + 1 < len(text) and text[i + 1] == '"':
                i += 2
                continue
            quoted = not quoted
        elif not quoted:
            if ch == '(':
                nesting += 1
            elif ch == ')':
                nesting -= 1
            elif nesting == 0:
                found = re.match(r'\s+ELSE\s+', text[i:], re.I)
                if found:
                    return text[:i].strip(), text[i + found.end():].strip()
        i += 1
    return None


def _indexed_assignment(statement):
    """Parsea A(i,j)=expr sin confundir ')', '=' o ',' de una cadena.

    El parser anterior usaba un grupo codicioso para los subindices y
    consumia el paréntesis final de un texto como "LOG_a(m*x+b) = k".
    """
    match = re.match(r'^([A-Za-z_][\w]*[$%!]?)\s*\(', statement)
    if not match:
        return None
    start = match.end()
    nesting = 1
    quoted = False
    i = start
    while i < len(statement):
        ch = statement[i]
        if ch == '"':
            if quoted and i + 1 < len(statement) and statement[i + 1] == '"':
                i += 2
                continue
            quoted = not quoted
        elif not quoted:
            if ch == '(':
                nesting += 1
            elif ch == ')':
                nesting -= 1
                if nesting == 0:
                    tail = statement[i + 1:]
                    assigned = re.match(r'^\s*=\s*(.+)$', tail, re.S)
                    if assigned:
                        return match.group(1), statement[start:i], assigned.group(1)
                    return None
        i += 1
    return None


class BasicArray:
    """Arreglo MMBasic rectangular (1 a 8 dimensiones) en memoria lineal.

    Cada cota de DIM es inclusiva. OPTION BASE define el menor índice
    de cada eje al crear el arreglo; cambiarlo después no modifica arrays.
    Los argumentos de rutina comparten el objeto original (BYREF).
    """

    MAX_ELEMENTS = 200_000
    MAX_DIMENSIONS = 8

    def __init__(self, name, upper_bounds, base, kind=None, string_length=None):
        self.name = name
        self.base = base
        self.kind = kind or ('STRING' if name.endswith('$') else 'INTEGER' if name.endswith('%') else 'FLOAT')
        self.string_length = string_length if self.kind == 'STRING' else None
        if isinstance(upper_bounds, int):
            upper_bounds = (upper_bounds,)
        self.upper_bounds = tuple(upper_bounds)
        if not 1 <= len(self.upper_bounds) <= self.MAX_DIMENSIONS:
            raise BasicError(f'DIM: numero de dimensiones invalido para {name}')

        self.shape = []
        size = 1
        for bound in self.upper_bounds:
            if isinstance(bound, bool) or not isinstance(bound, int) or bound < base:
                raise BasicError(f'DIM: limites invalidos para {name}')
            length = bound - base + 1
            if size > self.MAX_ELEMENTS // length:
                raise BasicError(f'DIM: arreglo demasiado grande: {name}')
            size *= length
            self.shape.append(length)
        self.shape = tuple(self.shape)
        self.upper_bound = self.upper_bounds[0] if len(self.shape) == 1 else None
        default = '' if self.kind == 'STRING' else 0
        self.items = [default] * size

    def _index(self, indices):
        if len(indices) != len(self.shape):
            raise BasicError(
                f'{self.name}: se esperaban {len(self.shape)} indices, '
                f'se recibieron {len(indices)}')
        # Orden fila mayor: último índice varía más rápido.
        position = 0
        for axis, (value, length) in enumerate(zip(indices, self.shape), 1):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not float('-inf') < value < float('inf')
                    or int(value) != value):
                raise BasicError(f'Indice invalido para {self.name}, eje {axis}: {value}')
            number = int(value)
            offset = number - self.base
            if offset < 0 or offset >= length:
                raise BasicError(f'Indice fuera de rango: {self.name}, eje {axis}: {number}')
            position = position * length + offset
        return position

    def read(self, indices):
        return self.items[self._index(indices)]

    def write(self, indices, value):
        position = self._index(indices)
        if self.kind == 'STRING' and not isinstance(value, str):
            raise BasicError(f'Tipo incorrecto en arreglo {self.name}')
        if self.kind != 'STRING' and isinstance(value, str):
            raise BasicError(f'Tipo incorrecto en arreglo {self.name}')
        if self.string_length is not None and len(value) > self.string_length:
            raise BasicError(f'{self.name}: longitud de cadena excedida ({self.string_length})')
        self.items[position] = value


class ScalarReference:
    """Referencia a un escalar del ambito del llamador (BYREF)."""

    def __init__(self, scope, name):
        self.scope = scope
        self.name = name

    def read(self):
        return self.scope.get(self.name, '' if self.name.endswith('$') else 0)

    def write(self, value):
        self.scope[self.name] = value


class ScopedVariables(MutableMapping):
    """Variables globales con un ámbito local por llamada de rutina.

    Las asignaciones no declaradas LOCAL se consideran globales en esta fase.
    """
    def __init__(self, keyboard=None, clock=None, wall_clock=None):
        self.keyboard = keyboard
        self.wall_clock = wall_clock if wall_clock is not None else datetime.now
        self.rtc_delta = timedelta(0)
        self.clock = clock if clock is not None else time.monotonic
        self.timer_origin = self.clock()
        self.timer_base_ms = 0
        self.globals = {}
        self.frames = []

    def _rtc_now(self):
        # Fecha/hora local de Linux. Los cambios desde BASIC son virtuales:
        # no alteran el reloj del sistema ni necesitan permisos de administrador.
        return self.wall_clock() + self.rtc_delta

    @staticmethod
    def _base_name(name):
        """MMBasic identifica nombres sin considerar el sufijo de tipo."""
        return name.rstrip('$%!').upper()

    def _check_conflict(self, name):
        """En un mismo ambito B%() y B$ no pueden coexistir.

        No mezclar marcos locales independientes: un LOCAL puede ocultar
        un simbolo global; la comprobacion solo afecta al marco visible.
        """
        for frame in reversed(self.frames):
            if name in frame:
                return
            conflict = any(self._base_name(other) == self._base_name(name)
                           and other != name for other in frame)
            if conflict:
                raise BasicError('Array Dimensions')
        if any(self._base_name(other) == self._base_name(name)
               and other != name for other in self.globals):
            raise BasicError('Array Dimensions')

    def __getitem__(self, name):
        if name == 'DATE$':
            return self._rtc_now().strftime('%d-%m-%Y')
        if name == 'TIME$':
            return self._rtc_now().strftime('%H:%M:%S')
        for frame in reversed(self.frames):
            if name in frame:
                value = frame[name]
                return value.read() if isinstance(value, ScalarReference) else value
        self._check_conflict(name)
        return self.globals[name]

    def __setitem__(self, name, value):
        if name == 'MM.CMDLINE$':
            raise BasicError('MM.CMDLINE$ es de solo lectura')
        if name in ('DATE$', 'TIME$'):
            if not isinstance(value, str):
                raise BasicError(f'{name}: se esperaba cadena')
            current = self._rtc_now()
            try:
                if name == 'DATE$':
                    # PicoMite: DD-MM-YYYY; tambien admitimos DD-MM-YY y '/' al ingresar.
                    match = re.fullmatch(r'(\d{1,2})[-/](\d{1,2})[-/](\d{2}|\d{4})', value.strip())
                    if not match:
                        raise ValueError('fecha fuera de formato')
                    day, month, year = map(int, match.groups())
                    if year < 100:
                        year += 2000
                    desired = current.replace(year=year, month=month, day=day)
                else:
                    match = re.fullmatch(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', value.strip())
                    if not match:
                        raise ValueError('hora fuera de formato')
                    hour, minute, second = match.groups()
                    desired = current.replace(hour=int(hour), minute=int(minute),
                                              second=int(second or 0), microsecond=0)
            except ValueError as exc:
                raise BasicError(f'{name}: valor invalido: {value}') from exc
            self.rtc_delta += desired - current
            return
        if name == 'TIMER':
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise BasicError('TIMER: se requiere numero de milisegundos')
            self.timer_origin = self.clock()
            self.timer_base_ms = value
            return
        for frame in reversed(self.frames):
            if name in frame:
                target = frame[name]
                if isinstance(target, ScalarReference):
                    target.write(value)
                else:
                    frame[name] = value
                return
        self._check_conflict(name)
        self.globals[name] = value

    def __delitem__(self, name):
        raise TypeError('No se eliminan variables BASIC')

    def __iter__(self):
        return iter(self.globals)

    def __len__(self):
        return len(self.globals)

    def get(self, name, default=None):
        if name in ('DATE$', 'TIME$'):
            return self[name]
        if name == 'TIMER':
            return self.timer_base_ms + max(0, int((self.clock() - self.timer_origin) * 1000))
        if name == "INKEY$" and self.keyboard is not None:
            return self.keyboard.read()
        try:
            return self[name]
        except KeyError:
            return default

    def declare_local(self, name, value):
        if not self.frames:
            raise BasicError('LOCAL fuera de SUB/FUNCTION')
        if name in self.frames[-1]:
            raise BasicError(f'Variable local duplicada: {name}')
        if any(self._base_name(existing) == self._base_name(name)
               and existing != name for existing in self.frames[-1]):
            raise BasicError('Array Dimensions')
        self.frames[-1][name] = value


class KeyboardBuffer:
    """Cola FIFO de caracteres, segura entre el hilo de Qt y el motor.

    INKEY$ no bloquea: si no hay teclas pendientes devuelve cadena vacia.
    Las teclas ASCII 8 y 13 se preservan para programas PicoCalc.
    """

    def __init__(self):
        self._keys = deque()
        self._lock = Lock()

    def push(self, text):
        if not isinstance(text, str):
            raise TypeError("Una tecla debe representarse como texto")
        with self._lock:
            self._keys.extend(text)

    def read(self):
        with self._lock:
            return self._keys.popleft() if self._keys else ""

    def clear(self):
        """Descarta caracteres de navegacion anteriores a una nueva entrada."""
        with self._lock:
            self._keys.clear()


class _FunctionSuspended(Exception):
    """Senal interna: FUNCTION cedio el control, sin perder su pila BASIC."""

    def __init__(self, result):
        self.result = result


class PersistentMemory:
    """Retained integer independent of A:/B:.

    A real RP2350 retains this over a reset, not power loss.  Desktop state
    has no equivalent to a hardware power-cycle; callers can reset/delete it.
    A missing path creates an isolated in-memory instance for unit tests.
    """
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else None
        self.number = 0
        if self.path is not None:
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(data, dict) and type(data.get('value')) is int:
                    self.number = data['value']
            except (FileNotFoundError, OSError, UnicodeError, ValueError):
                pass

    def save(self, value):
        if type(value) is not int or not -(1 << 63) <= value < (1 << 63):
            raise BasicError('SAVE PERSISTENT requiere INTEGER de 64 bits')
        if self.path is not None:
            _atomic_json_write(self.path, {'version': 1, 'value': value})
        self.number = value


def _atomic_json_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.persistent-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, path)
    except (OSError, ValueError, TypeError) as exc:
        raise BasicError(f'No se pudo guardar estado BASIC: {exc}') from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class BasicMachine:
    def __init__(self, source, *, keyboard=None, clock=None, drives=None, libraries=(),
                 persistent_store=None, cmdline=""):
        self.drives = drives
        self.source = source
        self.libraries = tuple(libraries)
        self.persistent_store = persistent_store if persistent_store is not None else PersistentMemory()
        self.program = []
        self.labels = {}
        self.line_ids = {}
        self.block_jumps = {}
        self.select_blocks = {}
        self.case_ends = {}
        self.do_loops = {}
        self.loop_starts = {}
        self.for_stack = []
        self.for_ends = {}
        self.do_stack = []
        self.gosub_stack = []
        self.keyboard = keyboard if keyboard is not None else KeyboardBuffer()
        self.clock = clock if clock is not None else time.monotonic
        self.pause_until = None
        self.option_base = 0
        self.option_explicit = False
        self.option_default = "FLOAT"
        self.variables = ScopedVariables(self.keyboard, self.clock)
        self.variables.angle_degrees = False
        self.variables.drives = drives
        self.routines = {}
        self.routine_modes = {}
        self.routine_types = {}
        self.routine_ends = {}
        self.call_stack = []
        self.function_depth = 0
        # Contextos de funciones suspendidas y resultados para reproducir
        # exclusivamente la sentencia que esperaba el valor de retorno.
        self._pending_functions = []
        self._completed_function_calls = {}
        self._current_statement = None
        # Salida producida por SUB llamados desde FUNCTION (p. ej., menus).
        self._deferred_output = []
        self._deferred_graphics = deque()
        self.pending_input = None
        self.enter_branch = None
        self.inline_pending = None
        self.pending_prompt = ""
        self.pc = 0
        self.instructions = 0
        self.finished = False
        self.rng = random.Random()
        self.foreground = 0x00FF00
        self.background = 0x000000
        self.active_font = 1
        self.font_scale = 1
        self._font_sizes = {}
        self.variables.mm_info = self._mm_info
        self._font_definitions = []
        # Diagnosticos no fatales. No forman parte de PRINT ni del framebuffer.
        self.warnings = []
        # ON ERROR es parte del estado de ejecución BASIC (no de la GUI).
        # SKIP protege las siguientes N sentencias, IGNORE hasta ABORT.
        self.file_handles = {}
        self._error_skip_remaining = 0
        self._error_ignore = False
        self._error_policy_generation = 0
        self.variables.globals['MM.ERRNO'] = 0
        self.variables.globals['MM.ERRMSG$'] = ''
        self.variables.globals['MM.VER'] = 6.0003
        self.variables.globals['MM.PERSISTENT'] = self.persistent_store.number
        self.variables.globals['MM.CMDLINE$'] = cmdline
        self.variables.file_eof = self._file_eof
        self.variables.dir_function = self._dir_function
        self._dir_results = iter(())
        # Las definiciones de biblioteca se agregan despues del programa.
        # No se modifican los archivos BAS originales.
        self._main_source_lines = len(source.splitlines())
        full_source = source + "\n" + "\n".join(libraries)
        # DEFINEFONT is a declaration containing hexadecimal words, not BASIC
        # instructions. Read it before the ordinary statement lexer sees it.
        # It is installed through the same typed graphics channel as TEXT.
        defining = None
        font_words = []
        for lineno, raw in enumerate(full_source.splitlines(), 1):
            text = _strip_comment(raw).strip()
            begin_font = re.fullmatch(r'DEFINEFONT\s+#?(\d+)', text, re.I)
            if begin_font and defining is None:
                defining = int(begin_font.group(1))
                font_words = []
                continue
            if defining is not None:
                if re.fullmatch(r'END\s+DEFINEFONT', text, re.I):
                    self._font_definitions.append(
                        self._decode_font(defining, font_words))
                    defining = None
                    continue
                if text:
                    # FileIO.c de PicoMite 6.00.03 acepta palabras
                    # hexadecimales contiguas, sin separadores.
                    compact = ''.join(text.split())
                    if (len(compact) % 8 or
                            re.fullmatch(r'[0-9A-Fa-f]*', compact) is None):
                        raise BasicError(f'DEFINEFONT: palabra hexadecimal invalida (linea {lineno})')
                    font_words.extend(compact[i:i + 8]
                                      for i in range(0, len(compact), 8))
                continue
            if not text:
                continue
            line_number = re.match(r'^(\d+)\s+(.+)$', text)
            if line_number:
                self.line_ids[int(line_number.group(1))] = len(self.program)
                text = line_number.group(2)
            label = re.fullmatch(r'([A-Za-z_][\w]*):', text)
            if label:
                self.labels[label.group(1).upper()] = len(self.program)
                continue
            # MMBasic: en "IF condicion THEN A : B", tanto A como B
            # pertenecen a la rama condicional. Separarlos primero haria que
            # B se ejecutase aun cuando la condicion fuese falsa. Expandimos
            # el IF de una linea a un bloque equivalente antes de indexar los
            # saltos. Las comillas y parentesis se respetan mediante _split.
            def append_statement(statement):
                statement = re.sub(r'^ELSE\s+IF\s+', 'ELSEIF ',
                                   statement, flags=re.I)
                match = re.match(r'^(IF\s+.+?\s+THEN)\s+(.+)$',
                                 statement, flags=re.I)
                branches = _split_inline_else(match.group(2)) if match else None
                if branches:
                    # IF X THEN A ELSE B, sin interpretar ELSE entre comillas.
                    true_branch, false_branch = branches
                    self.program.append((lineno, match.group(1)))
                    append_statement(true_branch.strip())
                    self.program.append((lineno, 'ELSE'))
                    append_statement(false_branch.strip())
                    self.program.append((lineno, 'END IF'))
                elif match and len(_split(match.group(2))) > 1:
                    self.program.append((lineno, match.group(1)))
                    for branch_statement in _split(match.group(2)):
                        if branch_statement:
                            append_statement(branch_statement)
                    self.program.append((lineno, 'END IF'))
                else:
                    self.program.append((lineno, statement))

            # Colones fuera de un IF de una linea siguen separando sentencias
            # independientes. Un IF precedido por otra instruccion tambien
            # debe conservar el resto de *su* rama condicional.
            pieces = _split(text)
            for index, statement in enumerate(pieces):
                if not statement:
                    continue
                if re.match(r'^IF\s+.+?\s+THEN\s+.+$', statement, re.I):
                    append_statement(':'.join(pieces[index:]))
                    break
                append_statement(statement)
        if defining is not None:
            raise BasicError('DEFINEFONT sin END DEFINEFONT')
        self._font_sizes = {
            command[1]: (command[2], command[3])
            for command in self._font_definitions
        }
        self._pending_fonts = deque(self._font_definitions)
        self._compile_blocks()
        self._compile_routines()
        self._index_data()

    @staticmethod
    def _decode_font(font_number, words):
        """DEFINEFONT de PicoMite 6.00.03, con datos binarios little-endian.

        El firmware acepta datos parciales y palabras adicionales. Se guardan
        los bits disponibles; se limita a la cantidad declarada al dibujar
        para evitar revelar el glifo sobrante. La memoria ausente es cero.
        """
        if not 1 <= font_number <= 16 or font_number in (1, 6, 7):
            raise BasicError('DEFINEFONT: numero de fuente no redefinible')
        blob = b''.join(bytes.fromhex(word)[::-1] for word in words)
        if len(blob) < 4:
            raise BasicError('DEFINEFONT: falta cabecera')
        width, height, first, count = blob[:4]
        # 6.00.03 impide definir codigos de control (< 32).
        if not (1 <= width <= 255 and 1 <= height <= 255 and first >= 32):
            raise BasicError('DEFINEFONT: cabecera invalida')
        # Los bits se concatenan en orden de glifo (no se rellena cada fila).
        # Corta solo el exceso; las definiciones parciales se preservan.
        needed = (width * height * count + 7) // 8
        payload = blob[4:4 + needed]
        return ('definefont', font_number, width, height, first, payload)

    @staticmethod
    def _mmbasic_select_expression(expression):
        """Admite ')' sobrantes al final como terminadores de MMBasic.

        No modifica el interior de una expresion ni ignora otros errores
        sintacticos. Respeta comillas y dobles comillas de las cadenas.
        """
        depth = 0
        quoted = False
        i = 0
        first_extra = None
        while i < len(expression):
            char = expression[i]
            if char == '"':
                if quoted and i + 1 < len(expression) and expression[i + 1] == '"':
                    i += 2
                    continue
                quoted = not quoted
            elif not quoted:
                if char == '(':
                    depth += 1
                elif char == ')':
                    if depth:
                        depth -= 1
                    else:
                        first_extra = i
                        break
            i += 1
        if first_extra is not None and expression[first_extra:].strip(' )') == '':
            return expression[:first_extra].rstrip(), expression[first_extra:].count(')')
        return expression, 0

    def _compile_blocks(self):
        """Indexa bloques para saltar ramas sin insertar instrucciones dinámicas."""
        conditional = []
        loops = []
        selects = []
        fors = []
        for i, (_, stmt) in enumerate(self.program):
            upper = stmt.upper()
            is_if = upper.startswith('IF ') and upper.endswith(' THEN')
            if is_if:
                conditional.append([i])
            elif upper == 'ELSE' or upper.startswith('ELSEIF '):
                if not conditional:
                    raise BasicError(f'{upper}: sin IF')
                self.block_jumps[conditional[-1][-1]] = i
                conditional[-1].append(i)
            elif upper in ('ENDIF', 'END IF'):
                if not conditional:
                    # El firmware 6.00.03 ejecuta END IF mediante cmd_null.
                    # Conservamos el analisis estricto, pero no rechazamos
                    # una instruccion que el dispositivo fisico admite.
                    self.warnings.append(
                        f'Warning: END IF sin IF de bloque '
                        f'(linea fuente {self.program[i][0]})'
                    )
                    continue
                chain = conditional.pop()
                self.block_jumps[chain[-1]] = i + 1
                for branch in chain:
                    self.block_jumps[('end', branch)] = i + 1
            elif upper.startswith('SELECT CASE '):
                # MMBasic evalua la expresion y admite que termine en ')'
                # aunque ese parentesis no tenga apertura correspondiente.
                # Reportamos la discrepancia sin impedir la ejecucion.
                expression = stmt[len('SELECT CASE '):].strip()
                _, extra = self._mmbasic_select_expression(expression)
                if extra:
                    self.warnings.append(
                        f'Warning: SELECT CASE con {extra} parentesis '
                        f'de cierre sobrante(s) (linea fuente '
                        f'{self.program[i][0]})'
                    )
                selects.append((i, []))
            elif upper == 'CASE ELSE' or upper.startswith('CASE '):
                if not selects:
                    raise BasicError('CASE sin SELECT CASE')
                selects[-1][1].append(i)
            elif upper in ('END SELECT', 'ENDSELECT'):
                if not selects:
                    raise BasicError('END SELECT sin SELECT CASE')
                start, branches = selects.pop()
                self.select_blocks[start] = (branches, i)
                for branch in branches:
                    self.case_ends[branch] = i + 1
            elif upper.startswith('FOR '):
                fors.append(i)
            elif upper == 'NEXT' or upper.startswith('NEXT '):
                if fors:
                    self.for_ends[fors.pop()] = i
            elif upper == 'DO' or upper.startswith('DO WHILE ') or upper.startswith('DO UNTIL '):
                loops.append(i)
            elif upper == 'LOOP' or upper.startswith('LOOP WHILE ') or upper.startswith('LOOP UNTIL '):
                if not loops:
                    raise BasicError('LOOP sin DO')
                start = loops.pop()
                self.do_loops[start] = i
                self.loop_starts[i] = start
        if conditional or loops or selects:
            # Un programa encadenado puede fallar *al compilar su destino*.
            # Informamos el origen exacto del bloque pendiente, en lugar de
            # sugerir que el problema esta en el RUN que acaba de salir.
            pending = []
            if conditional:
                pending.append((conditional[-1][0], 'IF', 'END IF'))
            if loops:
                pending.append((loops[-1], 'DO', 'LOOP'))
            if selects:
                pending.append((selects[-1][0], 'SELECT', 'END SELECT'))
            position, block, terminator = min(pending, key=lambda item: item[0])
            source_line = self.program[position][0]
            raise BasicError(
                f'Bloque {block} sin cerrar (linea fuente {source_line}; '
                f'falta {terminator})'
            )

    def _compile_routines(self):
        """Registra SUB/FUNCTION; sus cuerpos se omiten en el flujo principal."""
        current = None
        in_library = False
        declaration = re.compile(r'^(SUB|FUNCTION)\s+([A-Za-z_][\w]*[$%!]?)(?:\s*\((.*?)\)|\s+(.+))?$', re.I)
        for index, (line_number, statement) in enumerate(self.program):
            if current is not None and line_number > self._main_source_lines and not in_library:
                kind, start_index, name, declared_at = current
                raise BasicError(
                    f'Rutina {name} sin END {kind} (linea fuente {declared_at} '
                    f'del programa principal; antes de cargar la biblioteca)'
                )
            in_library = line_number > self._main_source_lines
            match = declaration.fullmatch(statement.strip())
            if match:
                if current is not None:
                    raise BasicError(
                        f'Rutinas anidadas no admitidas: {statement.strip()} '
                        f'(linea fuente {line_number}), dentro de {current[2]} '
                        f'(declarada en linea {current[3]})'
                    )
                kind, name, arg_parens, arg_plain = match.groups()
                params_raw = arg_parens if arg_parens is not None else (arg_plain or '')
                params = []
                modes = []
                types = []
                for part in _split(params_raw, ',') if params_raw else []:
                    raw = part.strip()
                    mode = re.match(r'^(BYVAL|BYREF)\s+', raw, flags=re.I)
                    if mode:
                        raw = raw[mode.end():]
                    typed = re.fullmatch(
                        r'([A-Za-z_][\w]*[$%!]?(?:\(\))?)'
                        r'(?:\s+AS\s+(STRING|INTEGER|FLOAT))?', raw, re.I
                    )
                    if not typed:
                        raise BasicError(f'Parametro no admitido: {part}')
                    formal, as_type = typed.groups()
                    suffix = formal[:-2] if formal.endswith('()') else formal
                    suffix = suffix[-1] if suffix[-1] in '$%!' else ''
                    expected = {'$': 'STRING', '%': 'INTEGER', '!': 'FLOAT'}.get(suffix)
                    if as_type and expected and as_type.upper() != expected:
                        raise BasicError(f'Parametro con tipos incompatibles: {part}')
                    params.append(formal.upper())
                    modes.append(mode.group(1).upper() if mode else 'AUTO')
                    types.append(as_type.upper() if as_type else expected)
                name = name.upper()
                if name in self.routines:
                    # El firmware no permite definir dos veces una rutina.
                    # No importa si procede del BAS principal o de una
                    # biblioteca: nunca elegimos una definicion en silencio.
                    raise BasicError(f'Rutina duplicada: {name}')
                self.routines[name] = (kind.upper(), index, params)
                self.routine_modes[name] = tuple(modes)
                self.routine_types[name] = tuple(types)
                current = (kind.upper(), index, name, line_number)
            elif statement.upper() in ('END SUB', 'END FUNCTION'):
                if current is None or statement.upper() != 'END '+current[0]:
                    raise BasicError('Cierre de rutina sin declaracion correspondiente')
                self.routine_ends[current[1]] = index
                current = None
        if current is not None:
            kind, _, name, line_number = current
            raise BasicError(f'Rutina {name} sin END {kind} (linea fuente {line_number})')

    def _index_data(self):
        """Prepara los DATA sin ejecutarlos; RESTORE apunta a sus offsets.

        Los numeros de linea precedentes a DATA son identificadores de
        nivel usados por Sokoban (por ejemplo RESTORE nivel con nivel=1).
        """
        self.data_values = []
        self.data_offsets = {}
        for position, (_, statement) in enumerate(self.program):
            if not statement.upper().startswith('DATA '):
                continue
            self.data_offsets[position] = len(self.data_values)
            for raw in _split(statement[5:], ','):
                item = raw.strip()
                if not item:
                    self.data_values.append(0)
                elif len(item) >= 2 and item[0] == item[-1] == '"':
                    self.data_values.append(item[1:-1].replace('""', '"'))
                elif re.fullmatch(r'[+-]?\d+', item):
                    self.data_values.append(int(item))
                elif re.fullmatch(r'[+-]?(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?', item):
                    self.data_values.append(float(item))
                else:
                    # MMBasic 6.00.03: READ de un STRING acepta DATA X
                    # sin comillas, y lo copia como texto literal. Rebound
                    # emplea DATA X / DATA XX como separadores de niveles.
                    # Nunca evaluamos estos identificadores como variables.
                    self.data_values.append(item)
        self.data_cursor = 0

    def _read_into(self, target):
        if self.data_cursor >= len(self.data_values):
            raise BasicError('READ: DATA agotados')
        value = self.data_values[self.data_cursor]
        name = target.strip().upper()
        indexed = re.fullmatch(r'([A-Z_][A-Z_0-9]*[$%!]?)\s*\((.*)\)', name)
        if indexed:
            array = self.variables.get(indexed.group(1))
            if not isinstance(array, BasicArray):
                raise BasicError(f'READ: arreglo no declarado: {indexed.group(1)}')
            indices = [self.value(x) for x in _split(indexed.group(2), ',')]
            array.write(indices, value)
        elif re.fullmatch(r'[A-Z_][A-Z_0-9]*[$%!]?', name):
            self.assign(name, value)
        else:
            raise BasicError(f'READ: destino invalido: {target}')
        self.data_cursor += 1

    def _start_routine(self, name, args, kind, arg_sources=None):
        routine = self.routines.get(name.upper())
        if routine is None or routine[0] != kind:
            raise BasicError(f'{kind} no disponible: {name}')
        _, start, params = routine
        if len(params) != len(args):
            raise BasicError(f'{name}: se esperaban {len(params)} argumentos')
        if len(self.call_stack) >= 64:
            raise BasicError('Demasiadas llamadas anidadas')
        frame = {}
        modes = self.routine_modes.get(name.upper(), ())
        types = self.routine_types.get(name.upper(), ())
        for index, (formal, actual) in enumerate(zip(params, args)):
            mode = modes[index] if index < len(modes) else 'AUTO'
            declared_type = types[index] if index < len(types) else None
            source = arg_sources[index].strip().upper() if arg_sources is not None else ''
            scalar_source = bool(re.fullmatch(r'[A-Z_][A-Z_0-9]*[$%!]?', source))
            # En MMBasic, BYREF es el comportamiento por defecto cuando
            # el argumento es una variable con tipo compatible.
            if mode == 'BYREF' and not scalar_source and not formal.endswith('()'):
                raise BasicError(f'{name}: BYREF {formal} requiere variable')
            if not formal.endswith('()'):
                if declared_type == 'STRING':
                    if not isinstance(actual, str):
                        raise BasicError(f'{name}: {formal} requiere STRING')
                elif declared_type in ('INTEGER', 'FLOAT'):
                    if isinstance(actual, str) or isinstance(actual, BasicArray):
                        raise BasicError(f'{name}: {formal} requiere {declared_type}')
                    if declared_type == 'INTEGER':
                        actual = int(actual)
                    else:
                        actual = float(actual)
            is_reference = (mode == 'BYREF' or (mode == 'AUTO' and scalar_source))
            # Si hay que convertir el tipo, MMBasic pasa el valor, no una
            # referencia a otra variable de tipo incompatible.
            if is_reference and not formal.endswith('()'):
                if source.endswith('$') != (declared_type == 'STRING' if declared_type else formal.endswith('$')):
                    if mode == 'BYREF':
                        raise BasicError(f'{name}: tipo BYREF incompatible: {formal}')
                    is_reference = False
                if is_reference and declared_type == 'INTEGER' and not source.endswith('%'):
                    is_reference = False
                if is_reference and declared_type == 'FLOAT' and source.endswith('%'):
                    is_reference = False
            if is_reference and not formal.endswith('()'):
                scope = next((f for f in reversed(self.variables.frames) if source in f),
                             self.variables.globals)
                original = scope.get(source)
                frame[formal] = original if isinstance(original, ScalarReference) else ScalarReference(scope, source)
                continue
            if formal.endswith('()'):
                if not isinstance(actual, BasicArray):
                    raise BasicError(f'{name}: {formal} requiere arreglo')
                if formal[:-2].endswith('$') != actual.name.endswith('$'):
                    raise BasicError(f'{name}: tipo de arreglo incompatible {formal}')
                frame[formal[:-2]] = actual  # referencia al mismo arreglo, no copia
            else:
                if isinstance(actual, BasicArray):
                    raise BasicError(f'{name}: {formal} requiere escalar')
                frame[formal] = actual
        if kind == 'FUNCTION':
            frame[name.upper()] = '' if name.endswith('$') else 0
        self.call_stack.append((kind, name.upper(), self.pc, len(self.for_stack), len(self.gosub_stack)))
        self.variables.frames.append(frame)
        self.pc = start + 1

    def _finish_routine(self, expected=None):
        if not self.call_stack:
            raise BasicError('END/EXIT de rutina fuera de llamada')
        kind, name, resume, for_depth, gosub_depth = self.call_stack[-1]
        if expected is not None and kind != expected:
            raise BasicError('EXIT/END de tipo de rutina incorrecto')
        result = self.variables.frames[-1].get(name, 0)
        self.call_stack.pop()
        self.variables.frames.pop()
        del self.for_stack[for_depth:]
        del self.gosub_stack[gosub_depth:]
        self.pc = resume
        return result

    def _call_function(self, name, args):
        if name.upper() == 'EVAL':
            if len(args) != 1 or not isinstance(args[0], str):
                raise BasicError('EVAL: requiere una cadena')
            return self.value(args[0])
        # Tras una espera, la sentencia que hizo la llamada se reevalua.
        # El resultado ya calculado no debe ejecutar de nuevo la FUNCTION.
        # La clave incluye la profundidad de rutinas, para distinguir SUBs.
        caller = self._current_statement
        caller_depth = len(self.call_stack)
        cache_key = (caller_depth, caller)
        cached = self._completed_function_calls.get(cache_key, [])
        if cached:
            first_name, first_args, result = cached[0]
            if first_name == name.upper() and first_args == tuple(args):
                cached.pop(0)
                if not cached:
                    self._completed_function_calls.pop(cache_key, None)
                return result

        previous_depth = len(self.call_stack)
        self._start_routine(name, args, 'FUNCTION')
        context = (previous_depth, caller, name.upper(), tuple(args))
        self._pending_functions.append(context)
        self.function_depth += 1
        try:
            for _ in range(256):
                result = self._step_guarded()
                if result.output:
                    self._deferred_output.append(result.output)
                if result.graphics:
                    self._deferred_graphics.append(result.graphics)
                if result.state in ('waiting_time', 'waiting_input', 'chain'):
                    raise _FunctionSuspended(result)
                if result.state != 'running':
                    raise BasicError('END inesperado durante evaluacion de FUNCTION')
                if len(self.call_stack) == previous_depth:
                    self._pending_functions.pop()
                    return self._last_function_result
            # Una FUNCTION puede esperar una tecla mediante DO/INKEY$ sin
            # PAUSE. Ceder el control preservando su pila y estado es mas
            # fiel que declarar error por superar un presupuesto de pasos.
            raise _FunctionSuspended(StepResult('running'))
        except _FunctionSuspended:
            # La pila BASIC y la PC quedan donde se detuvo la FUNCTION.
            # step() continuara desde este mismo punto en una llamada futura.
            raise
        finally:
            self.function_depth -= 1

    def _context_path(self):
        if self.drives is None or self.drives.roots.get('A') is None:
            raise BasicError('SAVE/LOAD CONTEXT requiere A: montada')
        # Save in a single fixed file at the root of virtual flash A:.
        # Resolve protects against symlinks escaping the mounted root.
        return self.drives.resolve('A:/.basic-cde-context.json')

    def _save_context(self, *, clear=False):
        variables = {}
        for name, item in self.variables.globals.items():
            if name.startswith('MM.'):
                continue
            if isinstance(item, BasicArray):
                variables[name] = {'type': 'array', 'bounds': list(item.upper_bounds),
                                   'base': item.base, 'kind': item.kind,
                                   'string_length': item.string_length,
                                   'items': list(item.items)}
            elif isinstance(item, (int, float, str)) and not isinstance(item, bool):
                variables[name] = {'type': 'scalar', 'value': item}
        _atomic_json_write(self._context_path(), {'version': 1, 'variables': variables})
        if clear:
            for name in variables:
                self.variables.globals.pop(name, None)

    def _load_context(self, *, keep=False):
        path = self._context_path()
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError as exc:
            raise BasicError('LOAD CONTEXT: no hay contexto guardado') from exc
        except (OSError, UnicodeError, ValueError) as exc:
            raise BasicError(f'LOAD CONTEXT: archivo invalido: {exc}') from exc
        if (not isinstance(payload, dict) or payload.get('version') != 1 or
                not isinstance(payload.get('variables'), dict)):
            raise BasicError('LOAD CONTEXT: formato invalido')
        restored = {}
        try:
            for name, data in payload['variables'].items():
                if (not isinstance(name, str) or not re.fullmatch(r'[A-Z_][A-Z_0-9]*[$%!]?', name)
                        or not isinstance(data, dict)):
                    raise ValueError('identificador invalido')
                if data.get('type') == 'scalar':
                    value = data['value']
                    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                        raise ValueError('valor invalido')
                elif data.get('type') == 'array':
                    value = BasicArray(name, tuple(data['bounds']), int(data['base']),
                                       data['kind'], data.get('string_length'))
                    if len(value.items) != len(data['items']):
                        raise ValueError('cantidad de elementos invalida')
                    for idx, item in enumerate(data['items']):
                        if (value.kind == 'STRING') != isinstance(item, str):
                            raise ValueError('tipo de dato en arreglo')
                        if value.string_length is not None and len(item) > value.string_length:
                            raise ValueError('longitud de cadena en arreglo')
                        value.items[idx] = item
                else:
                    raise ValueError('tipo de dato desconocido')
                restored[name] = value
        except (KeyError, ValueError, TypeError, BasicError) as exc:
            raise BasicError(f'LOAD CONTEXT: datos invalidos: {exc}') from exc
        self.variables.globals.update(restored)
        if not keep:
            try:
                path.unlink()
            except OSError as exc:
                raise BasicError(f'LOAD CONTEXT: no se pudo liberar contexto: {exc}') from exc

    def _mm_info(self, option, argument=None):
        """Read-only subset of MM.INFO for PicoCalc MMBasic 6.0003.

        This information lives in the BASIC machine so evaluation inside
        SUB/FUNCTION sees the same font state as ordinary instructions.
        """
        from basic_cde.devices.rom_fonts import DIMENSIONS

        option = str(option).upper()
        if option in ('FONTWIDTH', 'FONTHEIGHT'):
            dimensions = self._font_sizes.get(self.active_font)
            if dimensions is None:
                dimensions = DIMENSIONS.get(self.active_font)
            if dimensions is None:
                raise BasicError(f'FONT {self.active_font}: fuente no definida')
            return dimensions[0 if option == 'FONTWIDTH' else 1] * self.font_scale
        if option == 'FONT':
            return self.active_font
        if option in ('HRES', 'VRES'):
            return 320
        if option == 'FCOLOUR':
            return self.foreground
        if option == 'BCOLOUR':
            return self.background
        if option == 'VERSION':
            return 6.0003
        if option == 'PERSISTENT':
            return self.persistent_store.number
        if option in ('FILESIZE', 'MODIFIED', 'EXISTS FILE', 'EXISTS DIR',
                      'FREE SPACE', 'DISK SIZE'):
            if self.drives is None:
                raise BasicError('MM.INFO: unidad no montada')
            if option in ('FREE SPACE', 'DISK SIZE'):
                path = self.drives.resolve('.', directory=True)
                usage = shutil.disk_usage(path)
                return usage.free if option == 'FREE SPACE' else usage.total
            if not isinstance(argument, str):
                raise BasicError('MM.INFO: se esperaba nombre de archivo')
            path = self.drives.resolve(argument)
            if option == 'EXISTS FILE':
                return int(path.is_file())
            if option == 'EXISTS DIR':
                return int(path.is_dir())
            if option == 'MODIFIED':
                if not path.exists():
                    raise BasicError(f'MM.INFO: ruta no encontrada: {argument}')
                return datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            if not path.is_file():
                raise BasicError(f'MM.INFO: archivo no encontrado: {argument}')
            return path.stat().st_size
        if option == 'DRIVE':
            drives = getattr(self.variables, 'drives', None)
            if drives is None:
                raise BasicError('MM.INFO(DRIVE): unidades no disponibles')
            return drives.current + ':'
        raise BasicError(f'MM.INFO: opcion no disponible: {option}')

    def value(self, expression):
        return evaluate(expression, self.variables, self.rng, self._call_function)

    @staticmethod
    def _check_reserved_identifier(name):
        """Nombres tomados por el parser MMBasic/PicoMite 6.00.03.

        TAB es funcion, PUSH y OUT son comandos PIO. En el firmware
        no son identificadores BASIC declarables ni variables escalares.
        """
        base = name.upper().rstrip('$%!')
        if base == 'TAB':
            raise BasicError('Variable name')
        if base in ('PUSH', 'OUT'):
            raise BasicError('missing Program statement')

    def assign(self, name, value, *, declaring=False):
        name = name.upper()
        self._check_reserved_identifier(name)
        if self.option_explicit and not declaring and name not in self.variables and name not in self.routines:
            raise BasicError(f'Variable no declarada: {name}')
        if isinstance(value, BasicArray):
            raise BasicError('No se puede asignar un arreglo a un escalar')
        if name.endswith('$') and not isinstance(value, str):
            raise BasicError(f'Se esperaba cadena: {name}')
        if not name.endswith('$') and isinstance(value, str):
            raise BasicError(f'Se esperaba numero: {name}')
        self.variables[name] = value

    def input_value(self, value):
        if self.pending_input is None:
            raise BasicError('No hay INPUT pendiente')
        variable = self.pending_input
        if variable.endswith('$'):
            self.assign(variable, value)
        else:
            # INPUT numerico: Enter sin caracteres equivale a cero.
            # La entrada de cadena sigue aceptando "" como cadena vacia.
            expression = value.strip()
            self.assign(variable, 0 if not expression else self.value(expression))
        self.pending_input = None
        self.pending_prompt = ''

    def goto(self, target):
        if isinstance(target, str):
            position = self.labels.get(target.upper())
        else:
            position = self.line_ids.get(int(target))
        if position is None:
            raise BasicError(f'Etiqueta/linea inexistente: {target}')
        self.pc = position

    def _jump(self, target):
        target = target.strip()
        self.goto(int(target) if target.isdigit() else target)

    @staticmethod
    def format(value):
        return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)

    @staticmethod
    def _normalize_print_tab_adjacency(text):
        """Separa TAB(expr) del item siguiente en PRINT (MMBasic).

        PRINT TAB(5)"Hola" y PRINT TAB(5);"Hola" son formas
        equivalentes. Solo se normaliza TAB al comienzo de un item;
        las cadenas entrecomilladas no se reinterpretan.
        """
        output = []
        i = 0
        inside_string = False
        item_start = True
        while i < len(text):
            ch = text[i]
            if ch == '"':
                if inside_string and i + 1 < len(text) and text[i + 1] == '"':
                    output.append('""')
                    i += 2
                    continue
                inside_string = not inside_string
            if not inside_string and ch in ';,':
                item_start = True
            if not inside_string and item_start:
                if ch.isspace():
                    output.append(ch)
                    i += 1
                    continue
                match = re.match(r'TAB\s*\(', text[i:], re.I)
                if match:
                    start = i + match.end()
                    depth = 1
                    j = start
                    quote = False
                    while j < len(text) and depth:
                        if text[j] == '"':
                            quote = not quote
                        elif not quote:
                            if text[j] == '(': depth += 1
                            elif text[j] == ')': depth -= 1
                        j += 1
                    if depth == 0:
                        k = j
                        while k < len(text) and text[k].isspace(): k += 1
                        if k < len(text) and text[k] not in ';,':
                            output.append(text[i:j])
                            output.append(';')
                            i = k
                            item_start = True
                            continue
                item_start = False
            output.append(ch)
            i += 1
        return ''.join(output)

    def _print(self, text):
        if not text:
            return '\n'
        text = self._normalize_print_tab_adjacency(text)
        # Detectar separadores sin romper argumentos de funciones o strings.
        result = ''
        current = ''
        quoted, nesting = False, 0
        for ch in text:
            if ch == '"': quoted = not quoted
            if not quoted and ch == '(': nesting += 1
            if not quoted and ch == ')': nesting -= 1
            if not quoted and nesting == 0 and ch in ';,':
                if current.strip(): result += self.format(self.value(current.strip()))
                if ch == ',': result += ' '
                current = ''
            else:
                current += ch
        if current.strip(): result += self.format(self.value(current.strip()))
        if not text.rstrip().endswith(';'):
            result += '\n'
        return result

    def _matches_case(self, expression, control):
        """Comprueba una clausula CASE sin evaluar ramas descartadas.

        Formas admitidas: lista de expresiones, rango ``a TO b`` y
        comparacion ``IS >= b``. Los identificadores y las funciones
        se resuelven con la semantica habitual del motor MMBasic.
        """
        for item in _split(expression, ','):
            item = item.strip()
            if not item:
                raise BasicError('CASE: expresion vacia')
            relation = re.fullmatch(r'IS\s*(<=|>=|<>|!=|=|<|>)\s*(.+)', item, re.I)
            if relation:
                operator, right_expression = relation.groups()
                right = self.value(right_expression)
                try:
                    matches = {
                        '<': lambda: control < right,
                        '<=': lambda: control <= right,
                        '>': lambda: control > right,
                        '>=': lambda: control >= right,
                        '=': lambda: control == right,
                        '<>': lambda: control != right,
                        '!=': lambda: control != right,
                    }[operator]()
                except TypeError as exc:
                    raise BasicError('CASE: tipos incompatibles') from exc
            else:
                interval = re.fullmatch(r'(.+?)\s+TO\s+(.+)', item, re.I)
                if interval:
                    low, high = (self.value(x) for x in interval.groups())
                    try:
                        matches = low <= control <= high
                    except TypeError as exc:
                        raise BasicError('CASE: tipos incompatibles') from exc
                else:
                    matches = control == self.value(item)
            if matches:
                return True
        return False

    def _scan_loop_exit(self):
        """EXIT DO usa el DO más interno que contiene la instrucción."""
        for start, finish in sorted(self.do_loops.items(), reverse=True):
            if start < self.pc - 1 <= finish:
                return finish + 1
        raise BasicError('EXIT DO fuera de DO')

    def _dir_function(self, pattern=None, kind='FILE'):
        """DIR$ secuencial de PicoMite sobre el directorio virtual actual."""
        if pattern is not None:
            if not isinstance(pattern, str) or not isinstance(kind, str):
                raise BasicError('DIR$: argumentos invalidos')
            if self.drives is None:
                raise BasicError('DIR$: unidad no montada')
            directory = self.drives.resolve('.', directory=True)
            try:
                entries = sorted(directory.iterdir(), key=lambda item: item.name.casefold())
            except OSError as exc:
                raise BasicError(f'DIR$: {exc}') from exc
            def matches(path):
                if kind == 'DIR' and not path.is_dir():
                    return False
                if kind == 'FILE' and not path.is_file():
                    return False
                return fnmatch.fnmatchcase(path.name.casefold(), pattern.casefold()) or (
                    pattern == '*.*' and path.is_file())
            self._dir_results = iter(path.name for path in entries if matches(path))
        return next(self._dir_results, '')

    def _file_eof(self, number):
        stream = self.file_handles.get(int(number))
        if stream is None:
            raise BasicError(f'EOF: canal no abierto: {number}')
        if not stream.readable():
            raise BasicError('EOF: canal no es de lectura')
        position = stream.tell()
        last = stream.read(1)
        stream.seek(position)
        return int(last == '')

    def _file_number(self, raw):
        number = self.value(raw.strip().removeprefix('#'))
        if (isinstance(number, bool) or not isinstance(number, (int, float))
                or int(number) != number or not 1 <= number <= 255):
            raise BasicError('Canal de archivo invalido')
        return int(number)

    def _open_basic_file(self, statement):
        match = re.fullmatch(r'OPEN\s+(.+?)\s+FOR\s+(INPUT|OUTPUT|APPEND)\s+AS\s+#?(.+)', statement, re.I)
        if match is None:
            raise BasicError('OPEN: sintaxis invalida')
        if self.drives is None:
            raise BasicError('OPEN requiere unidad montada')
        name_expr, mode, channel_expr = match.groups()
        name = self.value(name_expr)
        if not isinstance(name, str) or not name:
            raise BasicError('OPEN: nombre invalido')
        number = self._file_number(channel_expr)
        if number in self.file_handles:
            raise BasicError(f'OPEN: canal en uso: {number}')
        path = self.drives.resolve(name)
        if not path.parent.is_dir():
            raise BasicError(f'OPEN: directorio inexistente: {name}')
        mode = {'INPUT': 'r', 'OUTPUT': 'w', 'APPEND': 'a'}[mode.upper()]
        try:
            stream = path.open(mode, encoding='utf-8', newline='')
        except (OSError, UnicodeError) as exc:
            raise BasicError(f'OPEN: {exc}') from exc
        self.file_handles[number] = stream

    def _close_file(self, number):
        handle = self.file_handles.pop(number, None)
        if handle is None:
            raise BasicError(f'CLOSE: canal no abierto: {number}')
        handle.close()

    def _step_guarded(self):
        """ON ERROR SKIP N / IGNORE sin cambiar el flujo de ejecución BASIC.

        La cuenta se aplica a sentencias efectivamente iniciadas, no a
        pasos de espera de PAUSE/INPUT ni a frames gráficos pendientes.
        MM.ERRNO y MM.ERRMSG$ persisten hasta CLEAR, SKIP o IGNORE.
        """
        previous_steps = self.instructions
        previous_remaining = self._error_skip_remaining
        policy_generation = self._error_policy_generation
        protected = previous_remaining > 0 or self._error_ignore
        try:
            result = self._step_impl()
        except BasicError as exc:
            executed = self.instructions > previous_steps
            if executed and previous_remaining > 0:
                self._error_skip_remaining = previous_remaining - 1
            if not protected or not executed:
                raise
            self.variables.globals['MM.ERRNO'] = 1
            self.variables.globals['MM.ERRMSG$'] = str(exc)
            return StepResult('running')
        if (self.instructions > previous_steps and previous_remaining > 0
                and policy_generation == self._error_policy_generation):
            self._error_skip_remaining = previous_remaining - 1
        return result

    def step(self):
        """Un paso cooperativo; una FUNCTION puede esperar sin bloquear Qt.

        Cuando retorna una FUNCTION suspendida se reintenta solamente la
        sentencia llamadora, reutilizando el valor ya calculado. No se
        reconstruye la pila de variables locales ni se reinicia el DO.
        """
        if self._deferred_graphics:
            return StepResult('running', graphics=self._deferred_graphics.popleft())
        try:
            result = self._step_guarded()
        except _FunctionSuspended as suspended:
            result = suspended.result

        # Un END FUNCTION o EXIT FUNCTION puede haber terminado la llamada
        # que estaba esperando. Recuperar su sentencia llamadora sin repetir
        # la ejecucion de la propia FUNCTION.
        while (self._pending_functions and
               len(self.call_stack) == self._pending_functions[-1][0]):
            depth, caller, name, args = self._pending_functions.pop()
            if caller is None:
                raise BasicError('FUNCTION suspendida sin sentencia llamadora')
            key = (depth, caller)
            self._completed_function_calls.setdefault(key, []).append(
                (name, args, self._last_function_result))
            self.inline_pending = caller

        if self._deferred_output:
            output = ''.join(self._deferred_output) + result.output
            self._deferred_output.clear()
            result = StepResult(result.state, output=output,
                                prompt=result.prompt, next_program=result.next_program,
                                graphics=result.graphics)
        return result

    def _step_impl(self):
        if self._pending_fonts:
            return StepResult('running', graphics=self._pending_fonts.popleft())
        if self.pause_until is not None:
            if self.clock() < self.pause_until:
                return StepResult('waiting_time')
            self.pause_until = None
        if self.finished or (self.pc >= len(self.program) and self.inline_pending is None):
            self.finished = True
            for stream in self.file_handles.values():
                stream.close()
            self.file_handles.clear()
            return StepResult('finished')
        if self.pending_input is not None:
            return StepResult('waiting_input', prompt=self.pending_prompt)
        if self.inline_pending is not None:
            lineno, stmt = self.inline_pending
            self.inline_pending = None
        else:
            lineno, stmt = self.program[self.pc]
            self.pc += 1
        self.instructions += 1
        self._current_statement = (lineno, stmt)
        upper = stmt.upper()
        try:
            if upper.startswith('SUB ') or upper.startswith('FUNCTION '):
                self.pc = self.routine_ends[self.pc-1] + 1
                return StepResult('running')
            if upper in ('END SUB', 'END FUNCTION', 'EXIT SUB', 'EXIT FUNCTION'):
                kind = 'SUB' if upper.endswith('SUB') else 'FUNCTION'
                returned = self._finish_routine(kind)
                if kind == 'FUNCTION':
                    self._last_function_result = returned
                return StepResult('running')
            if upper == 'LOCAL' or upper.startswith('LOCAL '):
                local_body = stmt[5:].strip()
                type_match = re.match(r'^(INTEGER|FLOAT|STRING)\s+(.+)$', local_body, re.I)
                local_type = type_match.group(1).upper() if type_match else None
                if type_match:
                    local_body = type_match.group(2)
                for raw_name in _split(local_body, ','):
                    name = raw_name.strip().upper()
                    array_decl = re.fullmatch(r'([A-Z_][A-Z_0-9]*[$%!]?)\s*\((.+)\)', name)
                    if array_decl:
                        array_name, bounds = array_decl.groups()
                        limits = [self.value(part) for part in _split(bounds, ',')]
                        if not all(isinstance(v, (int, float)) and int(v) == v for v in limits):
                            raise BasicError(f'LOCAL: cotas invalidas para {array_name}')
                        # LOCAL N$() es STRING, igual que DIM N$().
                        # Respetar el tipo declarado y los sufijos del nombre.
                        array_kind = (local_type or
                                      ('STRING' if array_name.endswith('$') else
                                       'INTEGER' if array_name.endswith('%') else
                                       self.option_default)).upper()
                        if array_kind == 'NONE':
                            raise BasicError(f'LOCAL: tipo no especificado para {array_name}')
                        self.variables.declare_local(
                            array_name,
                            BasicArray(array_name, [int(v) for v in limits],
                                       self.option_base, kind=array_kind))
                        continue
                    # MMBasic permite inicializar una variable local al declararla:
                    # LOCAL X=penx+Sin(heading)*distancia
                    # La expresion se evalua ANTES de crear el nombre local,
                    # preservando el acceso a los argumentos y al ambito llamador.
                    initial = None
                    if '=' in name:
                        variable, expression = name.split('=', 1)
                        name = variable.strip()
                        if not re.fullmatch(r'[A-Z_][A-Z_0-9]*[$%!]?', name) or not expression.strip():
                            raise BasicError(f'LOCAL invalido: {raw_name.strip()}')
                        initial = self.value(raw_name.split('=', 1)[1].strip())
                    if not re.fullmatch(r'[A-Z_][A-Z_0-9]*[$%!]?', name):
                        raise BasicError(f'LOCAL invalido: {name}')
                    if local_type == 'STRING' and not name.endswith('$'):
                        # En MMBasic AS STRING o LOCAL STRING también
                        # permite el nombre sin sufijo. El tipo vive en
                        # la declaración, no en el identificador.
                        default = ''
                    else:
                        default = '' if name.endswith('$') else 0
                    if initial is not None and local_type == 'INTEGER':
                        if isinstance(initial, str):
                            raise BasicError('LOCAL INTEGER: valor no numerico')
                        initial = int(initial)
                    self.variables.declare_local(name, default if initial is None else initial)
                return StepResult('running')
            if upper.startswith('CALL '):
                stmt = stmt[5:].strip()
                upper = stmt.upper()
            # Invocacion de SUB: SALUDAR "HOLA" o SALUDAR("HOLA")
            sub_name = re.match(r'^([A-Za-z_][\w]*[$%!]?)\b', stmt)
            if sub_name and sub_name.group(1).upper() in self.routines and self.routines[sub_name.group(1).upper()][0] == 'SUB':
                name = sub_name.group(1).upper()
                arguments = stmt[len(sub_name.group(1)):].strip()
                if arguments.startswith('(') and arguments.endswith(')'):
                    arguments = arguments[1:-1]
                sources = _split(arguments, ',') if arguments else []
                values = [self.value(x) for x in sources]
                self._start_routine(name, values, 'SUB', arg_sources=sources)
                return StepResult('running')
            if upper.startswith('REM ') or upper == 'REM' or stmt.startswith("'"):
                return StepResult('running')
            if upper.startswith('LONGSTRING '):
                command_text = stmt[len('LONGSTRING '):].strip()
                op_match = re.match(r'^([A-Za-z0-9]+)\s*(.*)$', command_text)
                if not op_match:
                    raise BasicError('LONGSTRING: falta operacion')
                op, args_text = op_match.groups()
                if op.upper() == 'PRINT':
                    parts = _split(args_text.rstrip(';'), ',')
                    if len(parts) != 1:
                        raise BasicError('LONGSTRING PRINT #: canal no implementado')
                    result = longstring_as_text(longstring_contents(self.value(parts[0])))
                    return StepResult('running', output=result + ('' if args_text.endswith(';') else '\n'))
                if not args_text:
                    raise BasicError('LONGSTRING: faltan argumentos')
                longstring_command(op, _split(args_text, ','), self.value)
                return StepResult('running')
            if upper in ('END', 'STOP'):
                self.finished = True
                return StepResult('finished')
            if upper.startswith('DATA '):
                return StepResult('running')
            if upper == 'RESTORE' or upper.startswith('RESTORE '):
                if upper == 'RESTORE':
                    self.data_cursor = 0
                else:
                    source = stmt[8:].strip()
                    # RESTORE etiqueta: MMBasic tambien admite una etiqueta
                    # simbolica (p.ej. RESTORE edges), no solo numeros.
                    # Los nombres de etiquetas tienen prioridad frente a una
                    # variable homonima cuyo valor inicial seria cero.
                    if source.upper() in self.labels:
                        destination = self.labels[source.upper()]
                    else:
                        target = self.value(source)
                        if not isinstance(target, (int, float)) or int(target) != target:
                            raise BasicError('RESTORE: se requiere etiqueta o numero de linea')
                        destination = self.line_ids.get(int(target))
                        if destination is None:
                            raise BasicError(f'RESTORE: linea no encontrada: {target}')
                    position = next((i for i in sorted(self.data_offsets)
                                     if i >= destination), None)
                    if position is None:
                        raise BasicError('RESTORE: no hay DATA en el destino')
                    self.data_cursor = self.data_offsets[position]
                return StepResult('running')
            if upper == 'ON ERROR ABORT':
                self._error_policy_generation += 1
                self._error_skip_remaining = 0
                self._error_ignore = False
                return StepResult('running')
            if upper == 'ON ERROR IGNORE 1':
                # WebMite 6.00003 (PicoCalc fisica): IGNORE 1 permanece activo
                # ante multiples errores consecutivos, incluso con OPTION
                # EXPLICIT. No equivale a ON ERROR SKIP 1. Validado con
                # prueba fisica 2026-11-09 (PASO 1, PASO 2, FIN).
                self._error_policy_generation += 1
                self._error_skip_remaining = 0
                self._error_ignore = True
                self.variables.globals['MM.ERRNO'] = 0
                self.variables.globals['MM.ERRMSG$'] = ''
                return StepResult('running')
            if upper == 'ON ERROR IGNORE':
                self._error_policy_generation += 1
                self._error_skip_remaining = 0
                self._error_ignore = True
                self.variables.globals['MM.ERRNO'] = 0
                self.variables.globals['MM.ERRMSG$'] = ''
                return StepResult('running')
            if upper == 'ON ERROR CLEAR':
                self.variables.globals['MM.ERRNO'] = 0
                self.variables.globals['MM.ERRMSG$'] = ''
                return StepResult('running')
            if upper == 'ON ERROR SKIP' or upper.startswith('ON ERROR SKIP '):
                count_expr = stmt[len('ON ERROR SKIP'):].strip()
                count = self.value(count_expr) if count_expr else 1
                if (isinstance(count, bool) or not isinstance(count, (int, float))
                        or not math.isfinite(count) or int(count) != count
                        or not 1 <= count <= 1000000):
                    raise BasicError('ON ERROR SKIP: cantidad invalida')
                self._error_policy_generation += 1
                self._error_skip_remaining = int(count)
                self._error_ignore = False
                self.variables.globals['MM.ERRNO'] = 0
                self.variables.globals['MM.ERRMSG$'] = ''
                return StepResult('running')
            if upper.startswith('OPEN '):
                self._open_basic_file(stmt)
                return StepResult('running')
            if upper.startswith('CLOSE '):
                self._close_file(self._file_number(stmt[6:]))
                return StepResult('running')
            if upper.startswith('LINE INPUT ') and not upper.startswith('LINE INPUT #'):
                # LINE INPUT de consola: captura la linea completa como texto,
                # incluidos espacios y comas. Variante con indicador opcional.
                # Es distinto del canal LINE INPUT #n, variable$.
                body = stmt[len('LINE INPUT '):].strip()
                prompt = ''
                match = re.fullmatch(
                    r'("(?:[^"]|"")*")\s*[,;]\s*([A-Za-z_][A-Za-z_0-9]*\$)',
                    body, re.I)
                if match:
                    prompt = self.value(match.group(1))
                    name = match.group(2).upper()
                else:
                    name = body.upper()
                    if not re.fullmatch(r'[A-Z_][A-Z_0-9]*\$', name):
                        raise BasicError('LINE INPUT: sintaxis invalida')
                self.pending_input = name
                self.pending_prompt = prompt
                return StepResult('waiting_input', prompt=prompt)
            if upper.startswith('LINE INPUT #'):
                match = re.fullmatch(r'LINE\s+INPUT\s+#?(\d+)\s*,\s*([A-Za-z_]\w*\$)', stmt, re.I)
                if match is None:
                    raise BasicError('LINE INPUT #: sintaxis invalida')
                stream = self.file_handles.get(int(match.group(1)))
                if stream is None or not stream.readable():
                    raise BasicError('LINE INPUT #: canal no abierto para lectura')
                value = stream.readline()
                self.assign(match.group(2), value.rstrip('\r\n'))
                return StepResult('running')
            if upper.startswith('PRINT #'):
                match = re.match(r'PRINT\s+#?(\d+)\s*,\s*(.*)$', stmt, re.I)
                if match is None:
                    raise BasicError('PRINT #: sintaxis invalida')
                stream = self.file_handles.get(int(match.group(1)))
                if stream is None or not stream.writable():
                    raise BasicError('PRINT #: canal no abierto para escribir')
                stream.write(self._print(match.group(2)))
                stream.flush()
                return StepResult('running')
            if upper.startswith('READ '):
                for target in _split(stmt[5:].strip(), ','):
                    self._read_into(target)
                return StepResult('running')
            if upper.startswith('DRIVE '):
                if self.drives is None:
                    raise BasicError('Unidades virtuales sin configurar')
                self.drives.drive(self.value(stmt[6:].strip()))
                return StepResult('running')
            if upper.startswith('CHDIR '):
                if self.drives is None:
                    raise BasicError('Unidades virtuales sin configurar')
                self.drives.chdir(self.value(stmt[6:].strip()))
                return StepResult('running')
            # Operaciones de archivos documentadas para PicoMite 6.00.03.
            # Se ejecutan SOLO en las unidades virtuales montadas, con
            # comprobacion de rutas contra escapes/symlinks en VirtualDrives.
            if upper.startswith(('KILL ', 'MKDIR ', 'RMDIR ')):
                if self.drives is None:
                    raise BasicError('Operacion de archivo requiere unidad montada')
                verb, expression = stmt.split(None, 1)
                filename = self.value(expression)
                if not isinstance(filename, str):
                    raise BasicError(f'{verb.upper()}: se requiere nombre de archivo')
                getattr(self.drives, verb.lower())(filename)
                return StepResult('running')
            if upper.startswith('RENAME '):
                if self.drives is None:
                    raise BasicError('RENAME requiere unidad montada')
                match = re.fullmatch(r'RENAME\s+(.+?)\s+AS\s+(.+)', stmt, re.I)
                if match is None:
                    raise BasicError('RENAME: sintaxis invalida')
                src, dst = (self.value(field) for field in match.groups())
                if not isinstance(src, str) or not isinstance(dst, str):
                    raise BasicError('RENAME: se requieren nombres de archivo')
                self.drives.rename(src, dst)
                return StepResult('running')
            if upper.startswith('COPY '):
                if self.drives is None:
                    raise BasicError('COPY requiere unidad montada')
                match = re.fullmatch(r'COPY\s+(.+?)\s+TO\s+(.+)', stmt, re.I)
                if match is None:
                    raise BasicError('COPY: sintaxis invalida')
                src, dst = (self.value(field) for field in match.groups())
                if not isinstance(src, str) or not isinstance(dst, str):
                    raise BasicError('COPY: se requieren nombres de archivo')
                self.drives.copy(src, dst)
                return StepResult('running')
            if upper.startswith('SPRITE SHOW SAFE ') or upper.startswith('SPRITE SHOW ') or upper.startswith('SPRITE HIDE SAFE ') or upper.startswith('SPRITE HIDE ') or upper.startswith('SPRITE SWAP '):
                match = re.match(r'^SPRITE\s+(SHOW SAFE|SHOW|HIDE SAFE|HIDE|SWAP)\s+(.+)$',stmt,re.I)
                if match is None:
                    raise BasicError('SPRITE: argumentos invalidos')
                action = match.group(1).upper().replace(' ','_')
                fields = _split(match.group(2), ',')
                count = {'SHOW':(4,5),'SHOW_SAFE':(4,5,6),
                         'HIDE':(1,),'HIDE_SAFE':(1,), 'SWAP':(2,3)}[action]
                if len(fields) not in count or any(not f.strip() for f in fields):
                    raise BasicError(f'SPRITE {action}: argumentos invalidos')
                values = tuple(int(self.value(f.strip().removeprefix('#').strip())) for f in fields)
                if not 1 <= values[0] <= 64:
                    raise BasicError('SPRITE: numero fuera de rango')
                if action == 'SWAP' and not 1 <= values[1] <= 64:
                    raise BasicError('SPRITE SWAP: numero fuera de rango')
                return StepResult('running',graphics=('sprite_command',action,*values))
            if upper == 'SPRITE CLOSE ALL':
                return StepResult('running', graphics=('sprite_command', 'CLOSE_ALL'))
            if upper.startswith('SPRITE SET TRANSPARENT '):
                val = int(self.value(stmt[len('SPRITE SET TRANSPARENT '):].strip()))
                if not 0 <= val <= 15:
                    raise BasicError('SPRITE SET TRANSPARENT: color fuera de rango')
                return StepResult('running', graphics=('sprite_command', 'TRANSPARENT', val))
            if re.match(r'^SPRITE\s+(READ|WRITE|LOADPNG|LOADBMP|CLOSE)\s+', stmt, re.I):
                match = re.match(r'^SPRITE\s+(READ|WRITE|LOADPNG|LOADBMP|CLOSE)\s+(.+)$', stmt, re.I)
                action, body = match.group(1).upper(), match.group(2)
                parts = _split(body, ',')
                expected = {'READ': (5,), 'WRITE': (3, 4,), 'LOADPNG': (2, 3, 4),
                            'LOADBMP': (2, 4, 6), 'CLOSE': (1,)}[action]
                if len(parts) not in expected or any(not v.strip() for v in parts):
                    raise BasicError(f'SPRITE {action}: argumentos invalidos')
                ident = parts[0].strip().removeprefix('#').strip()
                number = int(self.value(ident))
                if number < 1 or number > 64:
                    raise BasicError('SPRITE: numero fuera de rango (1-64)')
                if action.startswith('LOAD'):
                    filename = self.value(parts[1])
                    if not isinstance(filename, str) or not filename:
                        raise BasicError('SPRITE: archivo invalido')
                    rest = tuple(int(self.value(v)) for v in parts[2:])
                    if action == 'LOADPNG':
                        transparent = rest[0] if len(rest) > 0 else 0
                        alphacut = rest[1] if len(rest) > 1 else 20
                        if not 0 <= transparent <= 15 or not 0 <= alphacut <= 255:
                            raise BasicError('SPRITE LOADPNG: transparencia invalida')
                    return StepResult('running', graphics=('sprite_load_file', action, number, filename, *rest))
                rest = tuple(int(self.value(v)) for v in parts[1:])
                return StepResult('running', graphics=('sprite_command', action, number, *rest))
            if upper.startswith('BLIT READ ') or upper.startswith('BLIT WRITE ') or upper.startswith('BLIT CLOSE ') or upper.startswith('BLIT LOAD '):
                # BLIT con buffers #1..#32, distinto del BLIT de seis coordenadas.
                match = re.match(r'^BLIT\s+(READ|WRITE|CLOSE|LOAD)\s+(.+)$', stmt, re.I)
                assert match is not None
                action = match.group(1).upper()
                fields = _split(match.group(2).strip(), ',')
                expected = {'READ': (5,), 'WRITE': (3, 5), 'CLOSE': (1,),
                            'LOAD': (2, 4, 6)}[action]
                if len(fields) not in expected or any(not item.strip() for item in fields):
                    raise BasicError(f'BLIT {action}: argumentos invalidos')
                number_text = fields[0].strip()
                if number_text.startswith('#'):
                    number_text = number_text[1:].strip()
                number = int(self.value(number_text))
                if not 1 <= number <= 32:
                    raise BasicError('BLIT: buffer fuera de rango (1-32)')
                if action == 'LOAD':
                    filename = self.value(fields[1])
                    if not isinstance(filename, str) or not filename.strip():
                        raise BasicError('BLIT LOAD: nombre invalido')
                    values = [int(self.value(item)) for item in fields[2:]]
                    return StepResult('running', graphics=('blit_load_file', number, filename, *values))
                values = [int(self.value(item)) for item in fields[1:]]
                return StepResult('running', graphics=('blit_buffer', action, number, *values))
            if upper.startswith('LOAD JPG ') or upper.startswith('LOAD IMAGE ') or upper.startswith('LOAD PNG '):
                # Archivo JPEG o BMP y coordenadas opcionales del extremo superior
                # izquierdo. La decodificacion se efectua en BasicSession, fuera
                # del parser y sin importar PySide6 en el interprete.
                fmt = ('JPG' if upper.startswith('LOAD JPG ') else
                       'PNG' if upper.startswith('LOAD PNG ') else 'IMAGE')
                body = stmt[9:] if fmt in ('JPG', 'PNG') else stmt[11:]
                parts = _split(body.strip(), ',')
                if not 1 <= len(parts) <= (5 if fmt == 'PNG' else 3) or any(not item.strip() for item in parts):
                    raise BasicError(f'LOAD {fmt}: argumentos invalidos')
                filename = self.value(parts[0])
                if not isinstance(filename, str) or not filename.strip():
                    raise BasicError(f'LOAD {fmt}: nombre de archivo invalido')
                coords = [self.value(item) for item in parts[1:]]
                if any(isinstance(v, str) or not isinstance(v, (float, int))
                       for v in coords):
                    raise BasicError(f'LOAD {fmt}: coordenadas invalidas')
                x = int(coords[0]) if coords else 0
                y = int(coords[1]) if len(coords) > 1 else 0
                extra = ()
                if fmt == 'PNG':
                    transparent = int(coords[2]) if len(coords) > 2 else 0
                    alphacut = int(coords[3]) if len(coords) > 3 else 20
                    if transparent < -1 or transparent > 15:
                        raise BasicError('LOAD PNG: transparent fuera de rango (-1..15)')
                    if alphacut < 0 or alphacut > 255:
                        raise BasicError('LOAD PNG: alphacut fuera de rango (0..255)')
                    extra = (transparent, alphacut)
                return StepResult('running', graphics=('load_raster', fmt, filename, x, y, *extra))
            if upper.startswith('SAVE PERSISTENT '):
                value = self.value(stmt[len('SAVE PERSISTENT '):].strip())
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value:
                    raise BasicError('SAVE PERSISTENT requiere INTEGER')
                self.persistent_store.save(int(value))
                self.variables.globals['MM.PERSISTENT'] = int(value)
                return StepResult('running')
            if upper == 'SAVE CONTEXT' or upper == 'SAVE CONTEXT CLEAR':
                self._save_context(clear=(upper == 'SAVE CONTEXT CLEAR'))
                return StepResult('running')
            if upper in ('LOAD CONTEXT', 'LOAD CONTEXT KEEP'):
                self._load_context(keep=(upper == 'LOAD CONTEXT KEEP'))
                return StepResult('running')
            if upper.startswith('SAVE IMAGE '):
                filename = self.value(stmt[len('SAVE IMAGE '):].strip())
                if not isinstance(filename, str) or not filename.strip():
                    raise BasicError('SAVE IMAGE requiere nombre de archivo')
                return StepResult('running', graphics=('save_image', filename))
            if upper.startswith('RUN ') or upper.startswith('CHAIN '):
                if self.drives is None:
                    raise BasicError('Unidades virtuales sin configurar')
                chaining = upper.startswith('CHAIN ')
                command = 'CHAIN' if chaining else 'RUN'
                args = _split(stmt[len(command):].strip(), ',')
                if not 1 <= len(args) <= 2 or not args[0]:
                    raise BasicError(f'{command}: se espera archivo y cmdline opcional')
                filename = self.value(args[0])
                cmdline = self.value(args[1]) if len(args) == 2 and args[1] else ''
                if not isinstance(filename, str) or not filename:
                    raise BasicError(f'{command} requiere nombre de archivo')
                if not isinstance(cmdline, str) or len(cmdline) > 255:
                    raise BasicError(f'{command}: cmdline debe ser texto de hasta 255 caracteres')
                return StepResult('chain', next_program=filename,
                                  cmdline=cmdline, preserve_variables=chaining)
            if upper == 'OPTION EXPLICIT':
                # MMBasic requiere declaraciones: el control de nombres es
                # independiente de los tipos y de los valores implícitos.
                self.option_explicit = True
                return StepResult('running')
            if upper.startswith('OPTION DEFAULT '):
                choice = upper[15:].strip()
                if choice not in ('NONE', 'FLOAT', 'INTEGER', 'STRING'):
                    raise BasicError(f'OPTION DEFAULT no disponible: {choice}')
                self.option_default = choice
                return StepResult('running')
            if upper.startswith('OPTION ANGLE '):
                choice = upper[13:].strip()
                if choice not in ('DEGREES', 'RADIANS'):
                    raise BasicError(f'OPTION ANGLE no disponible: {choice}')
                self.variables.angle_degrees = choice == 'DEGREES'
                return StepResult('running')
            if upper.startswith('OPTION BASE '):
                base = self.value(stmt[12:].strip())
                if base not in (0, 1):
                    raise BasicError('OPTION BASE: solo 0 o 1')
                self.option_base = int(base)
                return StepResult('running')
            if upper.startswith('DIM '):
                # Formas MMBasic: DIM FLOAT X=1, Y=2;
                # DIM X AS FLOAT, Y AS INTEGER; DIM A(3) AS FLOAT.
                body = stmt[4:].strip()
                prefix = re.match(r'^(FLOAT|INTEGER|STRING)\s+', body, re.I)
                common_type = prefix.group(1).upper() if prefix else None
                if prefix:
                    body = body[prefix.end():]
                for declaration in _split(body, ','):
                    declaration = declaration.strip()
                    match = re.fullmatch(
                        r'([A-Za-z_][\w]*[$%!]?)\s*(?:\((.*?)\))?'
                        r'(?:\s+LENGTH\s+(\d+))?'
                        r'(?:\s+AS\s+(FLOAT|INTEGER|STRING))?'
                        r'(?:\s*=\s*(.+))?', declaration, re.I)
                    if not match:
                        raise BasicError(f'DIM no admitido: {declaration}')
                    name, bounds, string_length_text, specified_type, initializer = match.groups()
                    name = name.upper()
                    self._check_reserved_identifier(name)
                    kind = (specified_type or common_type or ('STRING' if name.endswith('$') else 'INTEGER' if name.endswith('%') else self.option_default)).upper()
                    if kind == 'NONE':
                        raise BasicError(f'DIM: tipo no especificado para {name}')
                    string_length = None
                    if string_length_text is not None:
                        if kind != 'STRING':
                            raise BasicError('DIM LENGTH requiere STRING')
                        string_length = int(string_length_text)
                        if not 1 <= string_length <= 255:
                            raise BasicError('DIM LENGTH: rango 1 a 255')
                    if name in self.variables:
                        raise BasicError(f'DIM duplicado: {name}')
                    if bounds is None:
                        default = '' if kind == 'STRING' else 0
                        result = self.value(initializer) if initializer is not None else default
                        self.assign(name, result, declaring=True)
                        continue
                    subscripts = _split(bounds, ',')
                    if not 1 <= len(subscripts) <= BasicArray.MAX_DIMENSIONS:
                        raise BasicError(f'DIM: numero de dimensiones invalido para {name}')
                    limits = []
                    for expression in subscripts:
                        bound = self.value(expression)
                        if (isinstance(bound, bool) or not isinstance(bound, (int, float))
                                or not float('-inf') < bound < float('inf')
                                or int(bound) != bound):
                            raise BasicError(f'DIM: limite no entero para {name}')
                        limits.append(int(bound))
                    array = BasicArray(name, limits, self.option_base, kind=kind,
                                       string_length=string_length)
                    if initializer is not None:
                        initial = initializer.strip()
                        if not (initial.startswith('(') and initial.endswith(')')):
                            raise BasicError(f'DIM: inicializacion de arreglo no valida: {name}')
                        values = [self.value(item) for item in _split(initial[1:-1], ',')]
                        if len(values) != len(array.items):
                            raise BasicError(f'DIM: cantidad de elementos invalida: {name}')
                        for offset, value in enumerate(values):
                            if kind == 'STRING' and (not isinstance(value, str)
                                    or (string_length is not None and len(value) > string_length)):
                                raise BasicError(f'DIM: longitud o tipo de cadena invalido para {name}')
                            array.items[offset] = value
                    self.variables[name] = array
                return StepResult('running')
            if upper.startswith('CONST '):
                # Una declaración CONST puede definir varios nombres separados
                # por comas, como hace la calculadora RPN original.
                for declaration in _split(stmt[6:].strip(), ','):
                    match = re.fullmatch(r'([A-Za-z_][\w]*[$%!]?)\s*=\s*(.+)',
                                         declaration, re.I)
                    if not match:
                        raise BasicError(f'CONST invalida: {declaration}')
                    self.assign(match.group(1), self.value(match.group(2)), declaring=True)
                return StepResult('running')
            if upper.startswith('RANDOMIZE '):
                self.rng.seed(self.value(stmt[10:].strip()))
                return StepResult('running')
            if upper.startswith('PAUSE '):
                duration = self.value(stmt[6:].strip())
                if not isinstance(duration, (int, float)) or not 0 <= duration < float('inf'):
                    raise BasicError('PAUSE requiere milisegundos no negativos y finitos')
                self.pause_until = self.clock() + duration / 1000.0
                return StepResult('waiting_time' if duration else 'running')
            if upper.startswith('FRAMEBUFFER '):
                parts = stmt[len('FRAMEBUFFER '):].strip().split(None, 1)
                action = parts[0].upper()
                raw = parts[1].strip() if len(parts) > 1 else ''
                if action not in ('CREATE', 'LAYER', 'WRITE', 'COPY',
                                  'CLOSE', 'MERGE', 'WAIT'):
                    raise BasicError('FRAMEBUFFER: comando no disponible')
                values = []
                if raw:
                    if action in ('CREATE', 'LAYER', 'WAIT'):
                        raise BasicError('FRAMEBUFFER: argumentos invalidos')
                    for token in _split(raw, ','):
                        token = token.strip()
                        if action == 'MERGE':
                            if token.upper() == 'B':
                                values.append('B')
                            else:
                                values.append(self.value(token))
                        elif token.upper() in ('N', 'F', 'L', 'B'):
                            values.append(token.upper())
                        else:
                            # Se admite una variable de texto con N, F o L.
                            result = self.value(token)
                            values.append(str(result).upper())
                return StepResult('running', graphics=('framebuffer', action, *values))
            if upper == 'CLS' or upper.startswith('CLS '):
                color = int(self.value(stmt[4:])) if len(stmt) > 3 else self.background
                return StepResult('running', graphics=('cls', color))
            if upper.startswith('COLOR ') or upper.startswith('COLOUR '):
                start = 7 if upper.startswith('COLOUR ') else 6
                args = _split(stmt[start:], ',')
                if not 1 <= len(args) <= 2:
                    raise BasicError('COLOR: se esperan uno o dos colores')
                self.foreground = int(self.value(args[0]))
                if len(args) == 2: self.background = int(self.value(args[1]))
                return StepResult('running', graphics=('color', self.foreground, self.background))
            if upper.startswith('FONT '):
                args = [self.value(part) for part in _split(stmt[5:], ',')]
                if not 1 <= len(args) <= 2:
                    raise BasicError('FONT: argumentos invalidos')
                font_number = int(args[0])
                font_scale = int(args[1]) if len(args) == 2 else 1
                from basic_cde.devices.rom_fonts import DIMENSIONS
                if font_number not in DIMENSIONS and font_number not in self._font_sizes:
                    raise BasicError(f'FONT {font_number}: fuente no definida')
                if font_scale < 1 or font_scale > 8:
                    raise BasicError('FONT: escala fuera de rango')
                self.active_font, self.font_scale = font_number, font_scale
                return StepResult('running', graphics=('font', *args))
            for command in ('PIXEL', 'LINE', 'BOX', 'RBOX', 'CIRCLE', 'TEXT', 'POLYGON', 'BLIT'):
                if upper.startswith(command + ' '):
                    fields, extra_closes = _split_graphic_args(
                        stmt[len(command) + 1:])
                    if extra_closes:
                        warning = (
                            f'Warning: {command} con {extra_closes} parentesis '
                            f'de cierre sobrante(s) (linea fuente {lineno})'
                        )
                        if warning not in self.warnings:
                            self.warnings.append(warning)
                    args = [self.value(part) if part.strip() else None
                            for part in fields]
                    if command == 'BLIT' and len(args) != 6:
                        raise BasicError('BLIT: se esperan seis argumentos')
                    return StepResult('running', graphics=(command.lower(), *args))
            if upper == 'MEMORY':
                # MMBasic admite MEMORY tanto en READY como durante RUN.
                # El reporte virtual es estimativo, nunca cuotas reales del RP2350.
                from basic_cde.app.memory_report import memory_report
                return StepResult('running', output=memory_report(
                    self.source, self.variables,
                    library_size=sum(len(x.encode('utf-8')) for x in self.libraries)))
            if upper == 'PRINT' or upper.startswith('PRINT ') or stmt.startswith('?'):
                text = stmt[5:].strip() if upper.startswith('PRINT') else stmt[1:].strip()
                position = _parse_print_at(text)
                if position:
                    coords = _split(position[0], ',')
                    if not 1 <= len(coords) <= 3:
                        raise BasicError('PRINT @: coordenadas invalidas')
                    x = self.value(coords[0])
                    y = self.value(coords[1]) if len(coords)>1 and coords[1].strip() else None
                    mode = self.value(coords[2]) if len(coords)>2 and coords[2].strip() else 0
                    return StepResult('running', graphics=('print_at', x, y,
                                                            self._print(position[1]).rstrip('\n'), mode))
                return StepResult('running', output=self._print(text))
            if upper.startswith('INPUT '):
                body = stmt[6:].strip()
                # El separador es semantico: ; imprime '?', , lo suprime.
                # INPUT ""; X$ no debe sustituirse por 'X$?'.
                prompt = ''
                separator = None
                match = re.match(r'^((?:"(?:[^"]|"")*")|(?:[^,;]+))\s*([,;])\s*(.+)$', body)
                if match:
                    prompt = self.format(self.value(match.group(1)))
                    separator = match.group(2)
                    body = match.group(3)
                name = body.strip().upper()
                if not re.fullmatch(r'[A-Z_][A-Z_0-9]*\$?', name):
                    raise BasicError('INPUT múltiple no implementado')
                self.pending_input = name
                self.pending_prompt = (prompt + ('? ' if separator == ';' else '')
                                       if separator else '? ')
                return StepResult('waiting_input', prompt=self.pending_prompt)
            if upper.startswith('GOSUB '):
                self.gosub_stack.append(self.pc)
                self._jump(stmt[6:])
                return StepResult('running')
            if upper == 'RETURN':
                if not self.gosub_stack:
                    raise BasicError('RETURN sin GOSUB')
                self.pc = self.gosub_stack.pop()
                return StepResult('running')
            if upper.startswith('GOTO '):
                self._jump(stmt[5:])
                return StepResult('running')
            if upper.startswith('SELECT CASE '):
                start = self.pc - 1
                choices, end = self.select_blocks[start]
                expression, _ = self._mmbasic_select_expression(
                    stmt[len('SELECT CASE '):].strip())
                control = self.value(expression)
                default = None
                for branch in choices:
                    clause = self.program[branch][1][5:].strip()
                    if clause.upper() == 'ELSE':
                        default = branch
                        continue
                    if self._matches_case(clause, control):
                        self.pc = branch + 1
                        break
                else:
                    self.pc = default + 1 if default is not None else end + 1
                return StepResult('running')
            if upper == 'CASE ELSE' or upper.startswith('CASE '):
                # Se llega aqui al terminar una rama ya seleccionada:
                # las restantes no deben ejecutarse.
                self.pc = self.case_ends[self.pc - 1]
                return StepResult('running')
            if upper in ('END SELECT', 'ENDSELECT'):
                return StepResult('running')
            if upper.startswith('IF ') and upper.endswith(' THEN'):
                condition = stmt[3:-5].strip()
                if not self.value(condition):
                    next_branch = self.block_jumps[self.pc-1]
                    self.pc = next_branch
                    self.enter_branch = next_branch
                return StepResult('running')
            if upper.startswith('IF '):
                match = re.match(r'^IF\s+(.+?)\s+THEN\s+(.+)$', stmt, re.I)
                if not match:
                    raise BasicError('IF requiere THEN')
                if self.value(match.group(1)):
                    target = match.group(2).strip()
                    if target.isdigit():
                        self._jump(target)
                    else:
                        self.inline_pending = (lineno, target)
                return StepResult('running')
            if upper.startswith('ELSEIF '):
                branch = self.pc - 1
                if self.enter_branch != branch:
                    self.pc = self.block_jumps[('end', branch)]
                else:
                    self.enter_branch = None
                    condition = re.match(r'ELSEIF\s+(.+?)\s+THEN$', stmt, re.I)
                    if condition is None:
                        raise BasicError('ELSEIF requiere THEN')
                    if not self.value(condition.group(1)):
                        next_branch = self.block_jumps[branch]
                        self.pc = next_branch
                        self.enter_branch = next_branch
                return StepResult('running')
            if upper == 'ELSE':
                branch = self.pc - 1
                if self.enter_branch != branch:
                    self.pc = self.block_jumps[('end', branch)]
                self.enter_branch = None
                return StepResult('running')
            if upper in ('ENDIF', 'END IF'):
                return StepResult('running')
            if upper == 'DO' or upper.startswith('DO WHILE ') or upper.startswith('DO UNTIL '):
                if upper.startswith('DO WHILE ') and not self.value(stmt[9:]):
                    self.pc = self.do_loops[self.pc-1]+1
                elif upper.startswith('DO UNTIL ') and self.value(stmt[9:]):
                    self.pc = self.do_loops[self.pc-1]+1
                return StepResult('running')
            if upper == 'LOOP' or upper.startswith('LOOP WHILE ') or upper.startswith('LOOP UNTIL '):
                start = self.loop_starts[self.pc-1]
                if upper == 'LOOP' or (upper.startswith('LOOP WHILE ') and self.value(stmt[11:])) or (upper.startswith('LOOP UNTIL ') and not self.value(stmt[11:])):
                    self.pc = start
                return StepResult('running')
            if upper == 'CONTINUE DO':
                starts = [(start, finish) for start, finish in self.do_loops.items()
                          if start < self.pc - 1 < finish]
                if not starts:
                    raise BasicError('CONTINUE DO fuera de DO')
                self.pc = max(starts)[1]
                return StepResult('running')
            if upper == 'EXIT DO':
                self.pc = self._scan_loop_exit()
                return StepResult('running')
            if upper == 'CONTINUE FOR':
                if not self.for_stack:
                    raise BasicError('CONTINUE FOR fuera de FOR')
                # NEXT incrementa la variable de control y decide si
                # corresponde repetir. No alterar la pila FOR aqui.
                # Buscar el NEXT emparejado, no el de un bucle anidado.
                name, last, delta, resume = self.for_stack[-1]
                end = self.for_ends.get(resume - 1)
                if end is None:
                    raise BasicError('CONTINUE FOR: NEXT correspondiente no encontrado')
                self.pc = end
                return StepResult('running')
            if upper == 'EXIT FOR':
                if not self.for_stack:
                    raise BasicError('EXIT FOR fuera de FOR')
                # The stack frame stores the instruction index immediately
                # after FOR.  EXIT FOR must skip its matching NEXT, not the
                # nearest NEXT from an unrelated/nested loop.
                name, last, delta, resume = self.for_stack.pop()
                end = self.for_ends.get(resume - 1)
                if end is None:
                    raise BasicError('EXIT FOR: NEXT correspondiente no encontrado')
                self.pc = end + 1
                return StepResult('running')
            if upper.startswith('PLAY TONE '):
                # PicoMite 6.00.03: PLAY TONE left,right[,duration[,interrupt]].
                # Audio via sesion: nunca bloquea la ejecucion del BASIC.
                fields = _split(stmt[len('PLAY TONE '):].strip(), ',')
                if not 2 <= len(fields) <= 4 or any(not f for f in fields):
                    raise BasicError('PLAY TONE: sintaxis invalida')
                if len(fields) == 4:
                    # Aun no ofrecemos interrupciones temporizadas de audio;
                    # rechazarlas evita ejecutar el programa con semantica falsa.
                    raise BasicError('PLAY TONE: interrupcion aun no implementada')
                try:
                    left, right = (float(self.value(v)) for v in fields[:2])
                    duration = float(self.value(fields[2])) if len(fields) == 3 else None
                except (ValueError, TypeError, OverflowError) as exc:
                    raise BasicError('PLAY TONE: frecuencia o duracion invalida') from exc
                if (not all(math.isfinite(v) and 0 <= v <= 22050 for v in (left, right))
                        or duration is not None and
                        (not math.isfinite(duration) or duration < 0)):
                    raise BasicError('PLAY TONE: frecuencia (0..22050 Hz) o duracion invalida')
                if duration == 0:
                    # Audio.c (6.00.03): duracion cero no inicia ni
                    # interrumpe el tono que ya estuviera reproduciendose.
                    return StepResult('running')
                return StepResult('running', audio=('tone', left, right, duration))
            if upper.startswith('PLAY MODFILE '):
                filename = self.value(stmt[len('PLAY MODFILE '):].strip())
                if not isinstance(filename, str) or not filename.strip():
                    raise BasicError('PLAY MODFILE: nombre de archivo invalido')
                if not Path(filename).suffix:
                    filename += '.mod'
                if self.drives is None:
                    raise BasicError('PLAY MODFILE requiere unidad montada')
                path = self.drives.resolve(filename)
                if not path.is_file():
                    raise BasicError(f'PLAY MODFILE: archivo no encontrado: {filename}')
                return StepResult('running', audio=('modfile', str(path)))
            if upper == 'PLAY STOP':
                return StepResult('running', audio=('stop',))
            if upper.startswith('FOR '):
                m = re.fullmatch(r'FOR\s+([A-Za-z_][\w]*[$%!]?)\s*=\s*(.+?)\s+TO\s+(.+?)(?:\s*STEP\b\s*(.+))?', stmt, re.I)
                if not m: raise BasicError('FOR invalido')
                name, start, finish, inc = m.groups()
                name = name.upper()
                first, last, delta = self.value(start), self.value(finish), self.value(inc) if inc else 1
                if delta == 0: raise BasicError('STEP cero')
                self.assign(name, first)
                if (delta > 0 and first > last) or (delta < 0 and first < last):
                    depth = 1
                    while self.pc < len(self.program) and depth:
                        current = self.program[self.pc][1].upper()
                        if current.startswith('FOR '): depth += 1
                        if current == 'NEXT' or current.startswith('NEXT '): depth -= 1
                        self.pc += 1
                else:
                    self.for_stack.append((name,last,delta,self.pc))
                return StepResult('running')
            if upper == 'NEXT' or upper.startswith('NEXT '):
                if not self.for_stack: raise BasicError('NEXT sin FOR')
                name,last,delta,resume = self.for_stack[-1]
                if upper != 'NEXT' and stmt[5:].strip().upper() != name:
                    raise BasicError('NEXT: variable incorrecta')
                self.assign(name,self.variables[name]+delta)
                if (delta > 0 and self.variables[name] <= last) or (delta < 0 and self.variables[name] >= last):
                    self.pc = resume
                else:
                    self.for_stack.pop()
                return StepResult('running')
            # INC/DEC modifican la variable conservando su ámbito.
            # Incremento omitido = 1. Usado por la tortuga de dragon.bas.
            if upper.startswith('INC ') or upper.startswith('DEC '):
                direction = 1 if upper.startswith('INC ') else -1
                parts = _split(stmt[4:].strip(), ',')
                if len(parts) not in (1, 2) or not re.fullmatch(r'[A-Za-z_][\w]*[$%!]?', parts[0].strip()):
                    raise BasicError('INC/DEC: argumentos invalidos')
                name = parts[0].strip().upper()
                amount = self.value(parts[1]) if len(parts) == 2 else 1
                if not isinstance(amount, (int, float)):
                    raise BasicError('INC/DEC: incremento no numerico')
                self.assign(name, self.variables[name] + direction * amount)
                return StepResult('running')
            if upper.startswith('LET '):
                stmt = stmt[4:].strip()
            # MM.CMDLINE$ es un valor del sistema de solo lectura.
            # Reconocer su asignacion antes del parser de variables normales,
            # que no admite nombres con punto.
            if re.match(r'^MM\.CMDLINE\$\s*=', stmt, re.I):
                raise BasicError('MM.CMDLINE$ es de solo lectura')
            indexed = _indexed_assignment(stmt)
            if indexed:
                name, subscripts, expression = indexed
                name = name.upper()
                self._check_reserved_identifier(name)
                arr = self.variables.get(name)
                if not isinstance(arr, BasicArray):
                    raise BasicError(f'Arreglo no declarado: {name}')
                indices = [self.value(x) for x in _split(subscripts, ',')]
                arr.write(indices, self.value(expression))
                return StepResult('running')
            m = re.fullmatch(r'([A-Za-z_][\w]*[$%!]?)[ ]*=[ ]*(.+)', stmt)
            if m:
                self.assign(m.group(1), self.value(m.group(2)))
                return StepResult('running')
            raise BasicError(f'Instruccion no disponible: {stmt}')
        except BasicError as exc:
            raise BasicError(f'{exc} (linea fuente {lineno})') from exc
        except (ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
            raise BasicError(f'{exc} (linea fuente {lineno})') from exc

    def run(self, input_provider=None, max_steps=100000):
        parts = []
        for _ in range(max_steps):
            result = self.step()
            parts.append(result.output)
            if result.state == 'finished':
                return ''.join(parts)
            if result.state == 'waiting_time':
                time.sleep(0.001)
            if result.state == 'waiting_input':
                if input_provider is None:
                    raise BasicError('INPUT pendiente: se requiere proveedor de entrada')
                self.input_value(input_provider(result.prompt))
        raise BasicError(f'Limite de {max_steps} instrucciones alcanzado')
