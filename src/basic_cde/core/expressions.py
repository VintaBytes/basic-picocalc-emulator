"""Evaluador seguro de expresiones BASIC: sin eval() ni exec().

La gramatica es deliberadamente reducida. No implementa aun los tipos de
MMBasic 6.00.01 completos; las incompatibilidades se detectan con error.
"""
import math
import struct
import random
import re
from dataclasses import dataclass


class BasicError(Exception):
    """Error de sintaxis o ejecucion BASIC visible para el usuario."""


_TOKEN_RE = re.compile(r'''\s*(?:(&[Hh][0-9A-Fa-f]+|&[Bb][01]+|&[Oo][0-7]+|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|("(?:""|[^"])*")|([A-Za-z_][A-Za-z_0-9.$%!]*)|(<=|>=|<>|<<|>>|[+*/^=(),<>\\#-]))''')


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def tokenize(source):
    out = []
    pos = 0
    while pos < len(source):
        if source[pos:].strip() == "":
            break
        match = _TOKEN_RE.match(source, pos)
        if match is None:
            raise BasicError(f"Caracter no reconocido en expresion: {source[pos:pos+15]!r}")
        num, string, name, operator = match.groups()
        if num is not None:
            out.append(Token("NUMBER", num))
        elif string is not None:
            out.append(Token("STRING", string[1:-1].replace('""', '"')))
        elif name is not None:
            out.append(Token("NAME", name.upper()))
        else:
            out.append(Token("OP", operator))
        pos = match.end()
    out.append(Token("EOF", ""))
    return out


# Precedencia provisional: se validara contra los vectores de PicoCalc.
_PRECEDENCE = {"OR": 1, "XOR": 2, "AND": 3,
               "=": 4, "<>": 4, "<": 4, ">": 4, "<=": 4, ">=": 4,
               "+": 5, "-": 5, "<<": 4.5, ">>": 4.5, "*": 6, "/": 6, "\\": 6, "MOD": 6, "^": 8}


# Atajos RGB(shortcut) documentados por PicoMite 6.00.03.
# Las denominaciones y alias proceden del manual; los valores de los tonos
# no primarios usan equivalentes RGB888 convencionales hasta contrastarlos
# numéricamente contra WebMite RP2350A 6.00003.
RGB_NAMED_COLORS = {
    "BLACK": 0x000000, "WHITE": 0xFFFFFF,
    "RED": 0xFF0000, "GREEN": 0x00FF00, "BLUE": 0x0000FF,
    "YELLOW": 0xFFFF00, "CYAN": 0x00FFFF, "MAGENTA": 0xFF00FF,
    "GOLD": 0xFFD700, "BROWN": 0xA52A2A, "ORANGE": 0xFFA500,
    "PINK": 0xFFC0CB, "SALMON": 0xFA8072, "BEIGE": 0xF5F5DC,
    "LIGHTGREY": 0xD3D3D3, "LIGHTGRAY": 0xD3D3D3,
    "GREY": 0x808080, "GRAY": 0x808080,
}


class ExpressionParser:
    def __init__(self, text, variables, randomizer=None, user_function=None):
        self.tokens = tokenize(text)
        self.i = 0
        self.variables = variables
        self.randomizer = randomizer or random.Random()
        self.user_function = user_function

    def peek(self):
        return self.tokens[self.i]

    def take(self):
        token = self.peek()
        self.i += 1
        return token

    def expect(self, symbol):
        if self.take().value != symbol:
            raise BasicError(f"Se esperaba {symbol}")

    def parse(self):
        result = self.expr(0)
        if self.peek().kind != "EOF":
            raise BasicError(f"Expresion sobrante: {self.peek().value}")
        return result

    def expr(self, minimum):
        token = self.take()
        if token.kind == "NUMBER":
            if token.value[:2].upper() in ('&H', '&B', '&O'):
                lhs = int(token.value[2:], {'H':16,'B':2,'O':8}[token.value[1].upper()])
            else:
                lhs = float(token.value) if any(x in token.value for x in '.eE') else int(token.value)
        elif token.kind == "STRING":
            lhs = token.value
        elif token.value == "(":
            lhs = self.expr(0)
            self.expect(")")
        elif token.value == "#":
            lhs = self.expr(7)
        elif token.value in ("+", "-", "NOT"):
            rhs = self.expr(7)
            lhs = (+rhs if token.value == "+" else -rhs if token.value == "-" else int(not rhs))
        elif token.kind == "NAME":
            # MATH(LOG10 expr) usa una palabra de operacion y un argumento,
            # no la sintaxis habitual LOG10(expr). La forma del manual
            # admite incluso una expresion dentro de los parentesis.
            if token.value == 'MATH' and self.peek().value == '(':
                self.take()
                operation = self.take()
                if operation.kind != 'NAME' or operation.value != 'LOG10':
                    raise BasicError(f'MATH: operacion no disponible: {operation.value}')
                argument = self.expr(0)
                self.expect(')')
                try:
                    lhs = math.log10(argument)
                except (ValueError, TypeError, OverflowError) as exc:
                    raise BasicError(f'MATH(LOG10): {exc}') from exc
            elif token.value in ('BIN2STR$', 'STR2BIN') and self.peek().value == '(':
                # En PicoMite los tokens de tipo (INT16, SINGLE, etc.) y BIG
                # son palabras reservadas en estas funciones, no variables.
                self.take()
                type_token = self.take()
                if type_token.kind != 'NAME':
                    raise BasicError(f'{token.value}: se esperaba un tipo')
                self.expect(',')
                argument = self.expr(0)
                big = False
                if self.peek().value == ',':
                    self.take()
                    endian = self.take()
                    if endian.kind != 'NAME' or endian.value != 'BIG':
                        raise BasicError(f'{token.value}: se esperaba BIG')
                    big = True
                self.expect(')')
                lhs = self.binary_conversion(token.value, type_token.value, argument, big)
            elif token.value == 'MM.INFO' and self.peek().value == '(':
                self.take()
                option = self.take()
                if option.kind != 'NAME':
                    raise BasicError('MM.INFO: argumento invalido')
                key = option.value
                if key in ('FREE', 'DISK', 'EXISTS') and self.peek().kind == 'NAME':
                    key += ' ' + self.take().value
                argument = None
                if self.peek().value != ')':
                    argument = self.expr(0)
                self.expect(')')
                resolver = getattr(self.variables, 'mm_info', None)
                if resolver is None:
                    raise BasicError('MM.INFO: no disponible')
                lhs = resolver(key, argument)
            elif token.value == 'INSTR' and self.peek().value == '(':
                # INSTR(start, cadena, patron, longitud): con cuatro
                # argumentos el patron es regex y el cuarto parametro
                # recibe el largo de la coincidencia por referencia.
                self.take()
                first = self.expr(0)
                self.expect(',')
                second = self.expr(0)
                if self.peek().value == ',':
                    self.take()
                    third = self.expr(0)
                else:
                    # INSTR(cadena, busqueda) sin posicion inicial.
                    first, second, third = 1, first, second
                if self.peek().value == ',':
                    self.take()
                    target = self.take()
                    if target.kind != 'NAME' or '.' in target.value:
                        raise BasicError('INSTR: tamaño debe ser variable')
                    self.expect(')')
                    if not isinstance(second, str) or not isinstance(third, str):
                        raise BasicError('INSTR: se esperaban cadenas')
                    pos = int(first)
                    if pos < 1:
                        raise BasicError('INSTR: posicion inicial invalida')
                    try:
                        found = re.search(third, second[pos - 1:])
                    except re.error as exc:
                        raise BasicError(f'INSTR: regex invalida: {exc}') from exc
                    self.variables[target.value] = len(found.group(0)) if found else 0
                    lhs = pos + found.start() if found else 0
                else:
                    self.expect(')')
                    if not isinstance(second, str) or not isinstance(third, str):
                        raise BasicError('INSTR: se esperaban cadenas')
                    if isinstance(first, str) or int(first) < 1:
                        raise BasicError('INSTR: posicion inicial invalida')
                    found_pos = second.find(third, int(first) - 1)
                    lhs = found_pos + 1 if found_pos >= 0 else 0
            elif token.value == 'DIR$' and self.peek().value == '(':
                # DIR$(pattern, DIR/FILE) utiliza palabras de filtro,
                # no variables BASIC; DIR$() continua la enumeracion.
                self.take()
                args = []
                if self.peek().value != ')':
                    args.append(self.expr(0))
                    if self.peek().value == ',':
                        self.take()
                        filter_token = self.take()
                        if filter_token.kind != 'NAME' or filter_token.value not in ('DIR', 'FILE', 'ALL'):
                            raise BasicError('DIR$: filtro invalido')
                        args.append(filter_token.value)
                self.expect(')')
                handler = getattr(self.variables, 'dir_function', None)
                if handler is None:
                    raise BasicError('DIR$: unidades virtuales no disponibles')
                lhs = handler(*args)
            elif self.peek().value == "(":
                self.take()
                args = []
                if self.peek().value != ")":
                    while True:
                        args.append(self.expr(0))
                        if self.peek().value != ",":
                            break
                        self.take()
                self.expect(")")
                maybe_array = self.variables[token.value] if token.value in self.variables else None
                if maybe_array is not None and hasattr(maybe_array, 'read') and hasattr(maybe_array, 'write'):
                    lhs = maybe_array if not args else maybe_array.read(args)
                else:
                    lhs = self.call(token.value, args)
            else:
                if token.value in ('PI', 'MM.HRES', 'MM.VRES') and token.value not in self.variables:
                    lhs = {'PI': math.pi, 'MM.HRES': 320, 'MM.VRES': 320}[token.value]
                elif token.value == 'RND':
                    # En MMBasic RND admite uso sin parentesis.
                    lhs = self.randomizer.random()
                elif token.value == 'CWD$' and hasattr(self.variables, 'drives') and self.variables.drives is not None:
                    lhs = self.variables.drives.cwd_string
                elif token.value == 'MM.INFO' and hasattr(self.variables, 'drives'):
                    raise BasicError('MM.INFO requiere argumento')
                elif token.value in RGB_NAMED_COLORS and token.value not in self.variables:
                    lhs = token.value
                else:
                    lhs = self.variables.get(token.value, "" if token.value.endswith("$") else 0)
        else:
            raise BasicError(f"Expresion invalida: {token.value}")
        while True:
            op = self.peek().value
            precedence = _PRECEDENCE.get(op)
            if precedence is None or precedence < minimum:
                break
            self.take()
            rhs = self.expr(precedence if op == "^" else precedence + 1)
            lhs = self.apply(op, lhs, rhs)
        return lhs

    def call(self, name, args):
        if name in ('LLEN', 'LGETBYTE', 'LGETSTR$', 'LINSTR', 'JSON$'):
            from .longstrings import long_function
            return long_function(name, args)
        if name == "INKEY$":
            if args:
                raise BasicError("INKEY$: no acepta argumentos")
            return self.variables.get("INKEY$", "")
        funcs = {"ABS": (1, abs), "INT": (1, math.floor), "SQR": (1, math.sqrt),
                 "SIN": (1, lambda v: math.sin(math.radians(v) if getattr(self.variables, "angle_degrees", False) else v)),
                 "COS": (1, lambda v: math.cos(math.radians(v) if getattr(self.variables, "angle_degrees", False) else v)),
                 "TAN": (1, lambda v: math.tan(math.radians(v) if getattr(self.variables, "angle_degrees", False) else v)),
                 "LOG": (1, math.log), "EXP": (1, math.exp),
                 "ASIN": (1, lambda v: self.inverse_angle(math.asin(v))),
                 "ACOS": (1, lambda v: self.inverse_angle(math.acos(v))),
                 "ATAN2": (2, lambda y, x: self.inverse_angle(math.atan2(y, x))),
                 "FIX": (1, math.trunc), "CINT": (1, self.cint),
                 "LEN": (1, len), "VAL": (1, self.val_number),
                 "CHR$": (1, lambda n: chr(int(n))), "ASC": (1, self.asc_value),
                 "RND": (0, self.randomizer.random),
                 "UCASE$": (1, lambda s: str(s).upper()),
                 "LCASE$": (1, lambda s: str(s).lower()),
                 "LEFT$": (2, lambda s,n: str(s)[:max(0,int(n))]),
                 "RIGHT$": (2, lambda s,n: str(s)[-int(n):] if int(n)>0 else ""),
                 "LJUST$": (2, lambda s,n: str(s).ljust(max(0,int(n)))),
                 "RJUST$": (2, lambda s,n: str(s).rjust(max(0,int(n)))),
                 "TAB": (1, lambda n: " " * max(0, int(n)-1)),
                 "SPACE$": (1, self.space),
                 "RAD": (1, math.radians), "DEG": (1, math.degrees),
                 "SGN": (1, lambda n: (n > 0) - (n < 0)),
                 "ATN": (1, lambda v: math.degrees(math.atan(v)) if getattr(self.variables, "angle_degrees", False) else math.atan(v)),
                 "STRING$": (2, self.string_repeat),
                 "RGB": (1, self.rgb_name)}
        if name == 'STR$':
            return self.str_number(args)
        # Funciones nativas de PicoMite 6.00.01: lista variable de numeros.
        # La comparacion y el resultado son de punto flotante.
        if name in ('MIN', 'MAX'):
            if not args or any(isinstance(v, (str, bool)) or
                               not isinstance(v, (int, float)) for v in args):
                raise BasicError(f'{name}: requiere al menos un numero')
            return float((min if name == 'MIN' else max)(args))
        if name in ('HEX$', 'BIN$', 'OCT$'):
            return self.base_string(name, args)
        if name == "FORMAT$" and len(args) == 2:
            if not isinstance(args[1], str) or not re.fullmatch(r'%[-+ 0#]*\d*(?:\.\d+)?[eEfFgGdi]', args[1]):
                raise BasicError('FORMAT$: formato no admitido')
            try:
                return args[1] % args[0]
            except (ValueError, TypeError, OverflowError) as exc:
                raise BasicError(f'FORMAT$: {exc}') from exc
        if name == 'EOF' and len(args) == 1 and hasattr(self.variables, 'file_eof'):
            return self.variables.file_eof(args[0])
        if name == "RGB" and len(args) == 3:
            return (int(args[0]) << 16) | (int(args[1]) << 8) | int(args[2])
        if name == "MID$" and len(args) in (2, 3):
            text, start = str(args[0]), max(0, int(args[1])-1)
            return text[start:] if len(args) == 2 else text[start:start+max(0,int(args[2]))]
        if name == "INSTR" and len(args) in (2, 3):
            # Posiciones MMBasic empiezan en 1; 0 significa no encontrado.
            if len(args) == 2:
                text, needle = args
                start = 1
            else:
                start, text, needle = args
            if (isinstance(start, bool) or not isinstance(start, (int, float))
                    or not math.isfinite(start) or int(start) != start
                    or start < 1):
                raise BasicError('INSTR: posicion inicial invalida')
            if not isinstance(text, str) or not isinstance(needle, str):
                raise BasicError('INSTR: se esperaban cadenas')
            found = text.find(needle, int(start) - 1)
            return found + 1 if found >= 0 else 0
        if name == "RND" and len(args) in (0,1):
            return self.randomizer.random()
        if name not in funcs:
            if self.user_function is not None:
                return self.user_function(name, args)
            raise BasicError(f"Funcion no disponible: {name}")
        required, fn = funcs[name]
        if len(args) != required:
            raise BasicError(f"{name}: se esperaban {required} argumentos")
        try:
            return fn(*args)
        except (ValueError, ZeroDivisionError, TypeError, IndexError, OverflowError) as exc:
            raise BasicError(f"{name}: {exc}") from exc

    def inverse_angle(self, radians):
        """Las inversas trigonometricas respetan OPTION ANGLE como ATN."""
        return (math.degrees(radians) if getattr(self.variables, 'angle_degrees', False)
                else radians)

    @staticmethod
    def str_number(args):
        """STR$(number[, width[, decimals[, pad$]]]) de MMBasic 6.00.03.

        Los parametros opcionales siguen fun_str de Functions.c; los FLOAT
        usan Decimal y quedan pendientes de contrastar en hardware.
        """
        from decimal import Decimal, ROUND_HALF_UP

        if not 1 <= len(args) <= 4:
            raise BasicError('STR$: se esperaban de 1 a 4 argumentos')
        number = args[0]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise BasicError('STR$: se esperaba un numero')

        def integer_option(value, minimum, maximum, label):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or int(value) != value
                    or not minimum <= value <= maximum):
                raise BasicError(f'STR$: {label} fuera de rango')
            return int(value)

        width = integer_option(args[1], -128, 128, 'ancho') if len(args) > 1 else 0
        decimals = integer_option(args[2], -20, 20, 'decimales') if len(args) > 2 else None
        pad = ' '
        if len(args) == 4:
            if not isinstance(args[3], str) or not args[3]:
                raise BasicError('STR$: caracter de relleno invalido')
            pad = chr(ord(args[3][0]) & 127)

        def padded(digits, sign=''):
            padding = max(0, abs(width) - len(digits))
            if sign:
                padding = max(1, padding)
                if pad == '0':
                    return sign + pad * (padding - 1) + digits
                return pad * (padding - 1) + sign + digits
            return pad * padding + digits

        if type(number) is int and (decimals is None or decimals >= 0):
            sign = '-' if number < 0 else ('+' if width < 0 else '')
            result = padded(str(abs(number)), sign)
            return result + ('.' + '0' * decimals if decimals else '')

        if not math.isfinite(number):
            return 'INF' if number > 0 else '-INF' if number < 0 else 'NAN'
        value = Decimal(str(number))
        exp = value.adjusted() if value else 0
        if decimals is None:
            scientific = bool(value and (abs(value) < Decimal('0.0001')
                                         or abs(value) >= Decimal('1000000')))
            places = 9 if scientific else max(0, 9 - exp)
        else:
            scientific = decimals < 0
            places = abs(decimals)
        if scientific and value:
            value = value.scaleb(-exp)
        value = value.quantize(Decimal(1).scaleb(-places),
                               rounding=ROUND_HALF_UP)
        if scientific and abs(value) >= 10:
            value /= 10
            exp += 1
        digits = format(abs(value), f'.{places}f')
        if decimals is None and '.' in digits:
            digits = digits.rstrip('0').rstrip('.')
        whole, point, frac = digits.partition('.')
        sign = '-' if value < 0 or (value == 0 and number < 0) else ('+' if width < 0 else '')
        result = padded(whole, sign) + ('.' + frac if point else '')
        return result + (f'e{exp:+03d}' if scientific else '')

    @staticmethod
    def asc_value(value):
        """MMBasic 6.00.03 Functions.c/fun_asc: ASC("") devuelve cero."""
        if not isinstance(value, str):
            raise BasicError('ASC: se esperaba una cadena')
        return ord(value[0]) if value else 0

    @staticmethod
    def cint(value):
        """Redondeo al entero mas proximo, .5 alejandose de cero.

        El comportamiento de empate requiere verificacion con PicoCalc real.
        """
        if isinstance(value, (str, bool)) or not isinstance(value, (int, float)):
            raise BasicError('CINT: se esperaba un numero')
        if not math.isfinite(value):
            raise BasicError('CINT: numero no finito')
        result = math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)
        if result < -(1 << 63) or result >= (1 << 63):
            raise BasicError('CINT: fuera de rango INTEGER de 64 bits')
        return result

    @staticmethod
    def base_string(name, args):
        """Conversion a bases 2/8/16 con relleno opcional de ceros.

        En negativos se expone el patron de 64 bits, como una variable
        INTEGER. Cotejar en PicoCalc el ancho de salidas negativas.
        """
        if len(args) not in (1, 2):
            raise BasicError(f'{name}: se esperaban 1 o 2 argumentos')
        value = args[0]
        if isinstance(value, (str, bool)) or not isinstance(value, (int, float)):
            raise BasicError(f'{name}: se esperaba un numero')
        if not math.isfinite(value):
            raise BasicError(f'{name}: numero no finito')
        number = math.trunc(value)
        if number < -(1 << 63) or number >= (1 << 64):
            raise BasicError(f'{name}: numero fuera de rango')
        base, fmt, limit = {'HEX$': (16, 'X', 16), 'BIN$': (2, 'b', 64),
                            'OCT$': (8, 'o', 22)}[name]
        count = 0
        if len(args) == 2:
            width = args[1]
            if (isinstance(width, (str, bool)) or not isinstance(width, (int, float))
                    or not math.isfinite(width) or int(width) != width
                    or width < 0 or width > limit):
                raise BasicError(f'{name}: ancho fuera de rango')
            count = int(width)
        if number < 0:
            number &= (1 << 64) - 1
        return format(number, fmt).zfill(count)

    @staticmethod
    def binary_conversion(name, binary_type, value, big=False):
        """PicoMite BIN2STR$/STR2BIN con tipo explicito y orden de bytes.

        Los caracteres de cadenas binarias representan bytes 0..255; no
        convertirlos a UTF-8 o alterar la longitud binaria.
        """
        layouts = {
            'INT8': ('b', 1, True), 'UINT8': ('B', 1, False),
            'INT16': ('h', 2, True), 'UINT16': ('H', 2, False),
            'INT32': ('i', 4, True), 'UINT32': ('I', 4, False),
            'INT64': ('q', 8, True), 'UINT64': ('Q', 8, False),
            'SINGLE': ('f', 4, None), 'DOUBLE': ('d', 8, None),
        }
        if binary_type not in layouts:
            raise BasicError(f'{name}: tipo no disponible: {binary_type}')
        code, length, signed = layouts[binary_type]
        endian = '>' if big else '<'
        if name == 'BIN2STR$':
            if isinstance(value, (str, bool)) or not isinstance(value, (int, float)):
                raise BasicError(f'{name}: se esperaba un numero')
            if not math.isfinite(value):
                raise BasicError(f'{name}: numero no finito')
            if signed is not None:
                integer = int(value)
                bits = length * 8
                lower = -(1 << (bits - 1)) if signed else 0
                upper = (1 << (bits - 1)) - 1 if signed else (1 << bits) - 1
                if not lower <= integer <= upper:
                    raise BasicError(f'{name}: valor fuera de rango {binary_type}')
                value = integer
            try:
                return struct.pack(endian + code, value).decode('latin-1')
            except (OverflowError, struct.error, ValueError) as exc:
                raise BasicError(f'{name}: {exc}') from exc
        if not isinstance(value, str) or len(value) != length:
            raise BasicError(f'{name}: cadena de longitud invalida para {binary_type}')
        try:
            raw = value.encode('latin-1')
        except UnicodeEncodeError as exc:
            raise BasicError(f'{name}: caracteres fuera del rango de bytes') from exc
        return struct.unpack(endian + code, raw)[0]

    @staticmethod
    def val_number(text):
        """VAL devuelve cero ante texto no numerico; acepta prefijos &H/&O/&B."""
        if not isinstance(text, str):
            raise BasicError('VAL: se esperaba una cadena')
        value = text.strip()
        if not value:
            return 0
        try:
            if re.fullmatch(r'[+-]?&[Hh][0-9a-fA-F]+', value):
                return int(value.replace('&H', '0x').replace('&h', '0x'), 16)
            if re.fullmatch(r'[+-]?&[Bb][01]+', value):
                return int(value.replace('&B', '0b').replace('&b', '0b'), 2)
            if re.fullmatch(r'[+-]?&[Oo][0-7]+', value):
                return int(value.replace('&O', '0o').replace('&o', '0o'), 8)
            if re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value):
                return float(value)
        except (ValueError, OverflowError):
            pass
        return 0

    @staticmethod
    def string_repeat(count, char):
        if (isinstance(count, (str, bool)) or not isinstance(count, (int, float))
                or not math.isfinite(count) or int(count) != count
                or not 0 <= count <= 255):
            raise BasicError('STRING$: longitud fuera de rango')
        if isinstance(char, str):
            if not char:
                raise BasicError('STRING$: cadena vacia')
            symbol = char[0]
        elif isinstance(char, (int, float)) and not isinstance(char, bool):
            if not math.isfinite(char) or int(char) != char or not 0 <= char <= 255:
                raise BasicError('STRING$: codigo ASCII fuera de rango')
            symbol = chr(int(char))
        else:
            raise BasicError('STRING$: segundo argumento invalido')
        return symbol * int(count)

    @staticmethod
    def space(count):
        """SPACE$(n): crea n espacios, con cantidad entera no negativa.

        Mantener una cota para que un programa defectuoso no consuma
        memoria sin limite por una sola expresion.
        """
        if (isinstance(count, bool) or not isinstance(count, (int, float))
                or not math.isfinite(count) or int(count) != count
                or not 0 <= count <= 255):
            raise BasicError(f'SPACE$: longitud fuera de rango: {count}')
        return ' ' * int(count)

    @staticmethod
    def rgb_name(name):
        if isinstance(name, (int, float)) and not isinstance(name, bool):
            if not float(name).is_integer() or not 0 <= name <= 0xFFFFFF:
                raise BasicError(f'Color RGB invalido: {name}')
            return int(name)
        key = str(name).upper()
        if key not in RGB_NAMED_COLORS:
            raise BasicError(f"Color RGB desconocido: {name}")
        return RGB_NAMED_COLORS[key]

    @staticmethod
    def apply(op, a, b):
        try:
            if op == "+": return a + b
            if op == "-": return a - b
            if op == "*": return a * b
            if op == "/": return a / b
            if op == "\\": return int(a / b)
            if op == "MOD": return a % b
            if op == "^": return a ** b
            if op == "=": return int(a == b)
            if op == "<>": return int(a != b)
            if op == "<": return int(a < b)
            if op == ">": return int(a > b)
            if op == "<=": return int(a <= b)
            if op == ">=": return int(a >= b)
            if op in ("<<", ">>"):
                # MMBasic operates on 64-bit integer bit patterns. The
                # incoming bits are zero; bits leaving the word are lost.
                if (not isinstance(a, (int, float)) or isinstance(a, bool)
                        or not isinstance(b, (int, float)) or isinstance(b, bool)
                        or not math.isfinite(a) or not math.isfinite(b)
                        or int(a) != a or int(b) != b):
                    raise BasicError("Shift: se requieren enteros")
                shift = int(b)
                if not 0 <= shift <= 63:
                    raise BasicError("Shift: cantidad fuera de rango")
                bits = int(a) & ((1 << 64) - 1)
                bits = ((bits << shift) if op == "<<" else (bits >> shift)) & ((1 << 64) - 1)
                return bits - (1 << 64) if bits & (1 << 63) else bits
            if op == "AND": return int(a) & int(b)
            if op == "OR": return int(a) | int(b)
            if op == "XOR": return int(a) ^ int(b)
        except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
            raise BasicError(f"Error en operador {op}: {exc}") from exc
        raise BasicError(f"Operador no disponible: {op}")


def evaluate(source, variables=None, randomizer=None, user_function=None):
    return ExpressionParser(source, variables if variables is not None else {}, randomizer, user_function).parse()
