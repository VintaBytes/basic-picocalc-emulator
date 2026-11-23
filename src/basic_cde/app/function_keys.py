"""Teclas de funcion configurables de PicoMite en el prompt READY.

OPTION F1 y OPTION F5..F9 se evalúan como expresiones BASIC. El texto
resultante se inyecta como pulsaciones, no como una sintaxis alternativa.
Estos ajustes pertenecen al entorno (flash), no al programa en memoria.
"""
import re

from basic_cde.core.expressions import BasicError, evaluate

CUSTOM_KEYS = (1, 5, 6, 7, 8, 9)
BUILTIN_KEYS = {2: 'RUN\r', 3: 'LIST\r', 4: 'EDIT\r'}


def parse_option_fn(statement):
    """Devuelve (numero, texto) o lanza BasicError con la misma sintaxis.

    Esta operacion se permite solo en READY, nunca dentro de un .BAS.
    """
    match = re.fullmatch(r'\s*OPTION\s+F(\d+)\s+(.+?)\s*', statement, re.I | re.S)
    if not match:
        raise BasicError('OPTION F: se esperaba OPTION F1/F5..F9 expresion$')
    number = int(match.group(1))
    if number not in CUSTOM_KEYS:
        raise BasicError('OPTION F: solo F1 y F5 a F9 son programables')
    value = evaluate(match.group(2))
    if not isinstance(value, str):
        raise BasicError('OPTION F: se esperaba una expresion de texto')
    if len(value) > 255:
        raise BasicError('OPTION F: texto demasiado largo')
    return number, value


def key_text(number, configured):
    if number in BUILTIN_KEYS:
        return BUILTIN_KEYS[number]
    return configured.get(number, '') if number in CUSTOM_KEYS else ''


def split_key_input(macro):
    """Convierte una macro en lineas confirmadas y una parte sin confirmar.

    CR LF consecutivos son un unico Enter (ejemplos del manual utilizan
    CHR$(13)+CHR$(10)). Una cadena sin CR/LF se inserta en el prompt,
    sin ejecutarse prematuramente.
    """
    if not isinstance(macro, str):
        raise TypeError('La macro debe ser una cadena')
    segments = re.split(r'\r\n|\r|\n', macro)
    return segments[:-1], segments[-1]
