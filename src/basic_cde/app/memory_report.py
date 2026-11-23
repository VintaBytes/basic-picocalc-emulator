"""MEMORY de BASIC CDE Linux, con las secciones de PicoCalc 6.0003.

Capacidades virtuales de referencia observadas por el usuario (PicoCalc
6.0003, 2026-11-08). El uso se estima desde el estado del interprete:
no representa el consumo real del firmware ni la RAM de Python.
"""
from __future__ import annotations

from basic_cde.core.machine import BasicArray

PROGRAM_CAPACITY = 208 * 1024
LIBRARY_CAPACITY = 208 * 1024
SAVED_CAPACITY = 16 * 1024
RAM_CAPACITY = 256 * 1024


def _kb(n):
    return max(0, (n + 1023) // 1024)


def _line(used, capacity, title):
    # Display en KB enteros como la maquina fisica.
    kb = _kb(used)
    total = capacity // 1024
    kb = min(total, kb)
    pct = round(100 * kb / total)
    return f"  {kb:3}K ({pct:3}%) {title}"


def _free(used, capacity):
    total = capacity // 1024
    remaining = max(0, total - _kb(used))
    pct = round(100 * remaining / total)
    return f"  {remaining:3}K ({pct:3}%) Free"


def memory_report(source: str, variables, *, program_capacity=PROGRAM_CAPACITY,
                  ram_capacity=RAM_CAPACITY, library_size=0,
                  library_capacity=LIBRARY_CAPACITY,
                  saved_size=0, saved_capacity=SAVED_CAPACITY) -> str:
    """Reproduce estructura de MEMORY, no cuotas reales de un PicoCalc."""
    # Los BAS en Python se almacenan como texto: no sabemos su tamaño tokenizado.
    # Se aproxima el almacenamiento de programa sin afectar ejecucion.
    program_size = len(source.encode('utf-8'))
    code_lines = sum(bool(line.strip()) for line in source.splitlines())
    symbols = [(key, value) for key, value in variables.items()
               if not key.startswith('MM.')]
    used_vars = 0
    for _, value in symbols:
        if isinstance(value, BasicArray):
            used_vars += 32 + sum(len(v.encode('utf-8')) if isinstance(v, str)
                                  else 8 for v in value.items)
        else:
            used_vars += 32 + (len(value.encode('utf-8')) if isinstance(value, str) else 8)
    return ('Program:\n'
            + _line(program_size, program_capacity,
                    f'Program ({code_lines} lines)') + '\n'
            + _free(program_size, program_capacity) + '\n\n'
            + 'Library:\n'
            + _line(library_size, library_capacity, 'Library') + '\n'
            + _free(library_size, library_capacity) + '\n\n'
            + 'Saved Variables:\n'
            + _free(saved_size, saved_capacity) + '\n\n'
            + 'RAM:\n'
            + _line(used_vars, ram_capacity, f'{len(symbols)} Variables') + '\n'
            + _line(0, ram_capacity, 'General') + '\n'
            + _free(used_vars, ram_capacity) + '\n')
