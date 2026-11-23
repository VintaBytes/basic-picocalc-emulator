"""Long strings PicoMite sobre el almacenamiento de arreglos INTEGER.

MMBasic reserva el primer elemento del arreglo para la longitud. Los
restantes contienen bytes en bloques little-endian de 8. No usamos una
segunda variable que pueda divergir de la memoria visible en BASIC.
"""
import json
import math
import re

from .expressions import BasicError


def require_array(value):
    # Duck typing, sin importar machine.py (evita dependencia circular).
    if not (hasattr(value, 'items') and hasattr(value, 'shape')
            and getattr(value, 'kind', None) == 'INTEGER'
            and len(value.shape) == 1):
        raise BasicError('LONGSTRING: se requiere un arreglo INTEGER de una dimension')
    return value


def _int(value, label, minimum=0):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or int(value) != value or value < minimum):
        raise BasicError(f'{label}: se esperaba entero >= {minimum}')
    return int(value)


def capacity(array):
    array = require_array(array)
    return (len(array.items) - 1) * 8


def contents(array):
    array = require_array(array)
    size = _int(array.items[0], 'LONGSTRING longitud')
    if size > capacity(array):
        raise BasicError('LONGSTRING: longitud fuera de la capacidad del arreglo')
    data = bytearray()
    for word in array.items[1:]:
        number = _int_word(word)
        data.extend(number.to_bytes(8, 'little', signed=False))
    return bytes(data[:size])


def _int_word(value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise BasicError('LONGSTRING: arreglo INTEGER contiene un valor no entero')
    if not -(1 << 63) <= value < (1 << 64):
        raise BasicError('LONGSTRING: palabra fuera de rango')
    return value & ((1 << 64) - 1)


def store(array, data):
    array = require_array(array)
    if len(data) > capacity(array):
        # En firmware un overflow de LONGSTRING es indefinido. Nuestra
        # proteccion evita corromper la memoria anfitriona; no se acepta
        # silenciosamente la escritura mas alla de la reserva.
        raise BasicError('LONGSTRING: capacidad insuficiente')
    array.items[0] = len(data)
    for i in range(1, len(array.items)):
        block = bytes(data[(i - 1) * 8:i * 8]).ljust(8, b'\0')
        array.items[i] = int.from_bytes(block, 'little', signed=True)


def as_bytes(value, label='LONGSTRING'):
    if not isinstance(value, str):
        raise BasicError(f'{label}: se esperaba una cadena')
    try:
        return value.encode('latin-1')
    except UnicodeEncodeError as exc:
        raise BasicError(f'{label}: caracteres fuera del juego de bytes') from exc


def as_text(data):
    return data.decode('latin-1')


def extract_json(array, selector):
    if not isinstance(selector, str):
        raise BasicError('JSON$: ruta debe ser una cadena')
    try:
        value = json.loads(as_text(contents(array)))
    except (ValueError, UnicodeError) as exc:
        raise BasicError('JSON$: documento JSON invalido') from exc
    if not selector:
        raise BasicError('JSON$: ruta vacia')
    # "list[4].weather[0].description" admite claves e indices.
    pos = 0
    while pos < len(selector):
        if selector[pos] == '.':
            pos += 1
            if pos == len(selector):
                raise BasicError('JSON$: ruta incompleta')
        if selector[pos] == '[':
            match = re.match(r'\[(\d+)\]', selector[pos:])
            if not match or not isinstance(value, list):
                raise BasicError('JSON$: indice invalido')
            index = int(match.group(1))
            try:
                value = value[index]
            except IndexError as exc:
                raise BasicError('JSON$: indice fuera de rango') from exc
            pos += len(match.group(0))
        else:
            match = re.match(r'[^.\[\]]+', selector[pos:])
            if not match or not isinstance(value, dict):
                raise BasicError('JSON$: ruta invalida')
            key = match.group(0)
            if key not in value:
                raise BasicError('JSON$: clave no encontrada')
            value = value[key]
            pos += len(key)
        if pos < len(selector) and selector[pos] not in '.[':
            raise BasicError('JSON$: sintaxis de ruta invalida')
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(',', ':'), ensure_ascii=False)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    return str(value)


def long_function(name, args):
    if name == 'JSON$':
        if len(args) != 2:
            raise BasicError('JSON$: requiere arreglo y ruta')
        return extract_json(args[0], args[1])
    if not args:
        raise BasicError(f'{name}: falta arreglo')
    data = contents(args[0])
    if name == 'LLEN':
        if len(args) != 1:
            raise BasicError('LLEN: requiere 1 argumento')
        return len(data)
    if name == 'LGETBYTE':
        if len(args) != 2:
            raise BasicError('LGETBYTE: requiere 2 argumentos')
        position = _int(args[1], 'LGETBYTE', 1)
        if position > len(data):
            raise BasicError('LGETBYTE: posicion fuera de rango')
        return data[position - 1]
    if name == 'LGETSTR$':
        if len(args) != 3:
            raise BasicError('LGETSTR$: requiere 3 argumentos')
        start = _int(args[1], 'LGETSTR$ inicio', 1)
        count = _int(args[2], 'LGETSTR$ cantidad')
        if count > 255:
            raise BasicError('LGETSTR$: maximo 255 bytes en cadena BASIC')
        return as_text(data[start - 1:start - 1 + count])
    if name == 'LINSTR':
        if len(args) not in (2, 3, 4):
            raise BasicError('LINSTR: requiere 2 a 4 argumentos')
        needle = as_bytes(args[1], 'LINSTR')
        start = _int(args[2], 'LINSTR inicio', 1) if len(args) >= 3 else 1
        if len(args) == 4:
            raise BasicError('LINSTR: busqueda regex aun no implementada')
        index = data.find(needle, start - 1)
        return index + 1 if index >= 0 else 0
    raise BasicError(f'Funcion LONGSTRING no disponible: {name}')


def command(verb, args, value):
    """Ejecuta un subconjunto fiel de los comandos LONGSTRING."""
    verb = verb.upper()
    if verb in ('CLEAR', 'LCASE', 'UCASE'):
        if len(args) != 1:
            raise BasicError(f'LONGSTRING {verb}: requiere 1 argumento')
        target = value(args[0])
        if verb == 'CLEAR':
            store(target, b'')
        elif verb == 'LCASE':
            store(target, contents(target).lower())
        else:
            store(target, contents(target).upper())
        return None
    if verb in ('APPEND', 'LOAD', 'COPY', 'CONCAT', 'LEFT', 'RIGHT', 'MID', 'RESIZE', 'SETBYTE'):
        expected = {'APPEND': (2,), 'LOAD': (3,), 'COPY': (2,), 'CONCAT': (2,),
                    'LEFT': (3,), 'RIGHT': (3,), 'MID': (3, 4),
                    'RESIZE': (2,), 'SETBYTE': (3,)}
        if len(args) not in expected[verb]:
            raise BasicError(f'LONGSTRING {verb}: cantidad de argumentos invalida')
        target = value(args[0])
        current = contents(target)
        if verb == 'APPEND':
            result = current + as_bytes(value(args[1]))
        elif verb == 'LOAD':
            count = _int(value(args[1]), 'LONGSTRING LOAD')
            result = as_bytes(value(args[2]))[:count]
        elif verb in ('COPY', 'CONCAT', 'LEFT', 'RIGHT', 'MID'):
            source = contents(value(args[1]))
            if verb == 'COPY':
                result = source
            elif verb == 'CONCAT':
                result = current + source
            else:
                if verb == 'LEFT':
                    result = source[:_int(value(args[2]), 'LONGSTRING LEFT')]
                elif verb == 'RIGHT':
                    count = _int(value(args[2]), 'LONGSTRING RIGHT')
                    result = source[-count:] if count else b''
                else:
                    start = _int(value(args[2]), 'LONGSTRING MID', 1)
                    count = (_int(value(args[3]), 'LONGSTRING MID') if len(args) == 4
                             else len(source))
                    result = source[start - 1:start - 1 + count]
        elif verb == 'RESIZE':
            size = _int(value(args[1]), 'LONGSTRING RESIZE')
            result = current[:size].ljust(size, b'\0')
        else:
            position = _int(value(args[1]), 'LONGSTRING SETBYTE', 1)
            number = _int(value(args[2]), 'LONGSTRING SETBYTE')
            if number > 255 or position > len(current):
                raise BasicError('LONGSTRING SETBYTE: posicion o byte invalido')
            changed = bytearray(current)
            changed[position - 1] = number
            result = bytes(changed)
        store(target, result)
        return None
    raise BasicError(f'LONGSTRING: operacion no implementada: {verb}')
