#!/usr/bin/env python3
"""Inventario y ejecucion aislada del corpus .BAS para BASIC PicoCalc Linux.

Ejemplo:
 python scripts/regresion_corpus_bas.py examples --out informe-corpus --timeout 2 --max-instructions 10000

Cada BAS se ejecuta desde una COPIA temporal del corpus; nunca se escribe en los
programas originales. Finalizar el proceso no equivale a validar la GUI ni el
comportamiento de juegos interactivos: sus resultados se etiquetan por separado.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

FIELDS = ["programa", "sha256", "bytes", "estado", "segundos", "retorno", "detalle", "salida"]


def classify(returncode: int, stderr: str, stdout: str, timed_out: bool) -> tuple[str, str]:
    if timed_out:
        return "TIEMPO_AGOTADO", "Limite de tiempo (podria ser programa interactivo)"
    whole = (stderr + "\n" + stdout).strip()
    if returncode == 0:
        return "TERMINA", "Finalizo sin error detectado en modo texto"
    if "EOFError" in whole or "EOF when reading a line" in whole:
        return "ESPERA_INPUT", "Solicito entrada de usuario"
    if "Limite configurado:" in whole:
        return "LIMITE_INSTRUCCIONES", "Alcanzo el presupuesto de instrucciones (puede ser bucle interactivo)"
    if "No such file" in whole or "No existe" in whole or "no encontrado" in whole.lower():
        return "ARCHIVO_FALTANTE", whole[-500:]
    if "ModuleNotFoundError" in whole:
        return "DEPENDENCIA", whole[-500:]
    if "?" in whole or "Traceback" in whole:
        return "ERROR", whole[-500:]
    return "SALIDA_NO_CERO", whole[-500:]


def run_one(program: Path, root: Path, python: str, src: Path, timeout: float,
            max_instructions: int) -> dict:
    relative = program.relative_to(root)
    start = time.monotonic()
    data = program.read_bytes()
    row = {"programa": relative.as_posix(), "sha256": hashlib.sha256(data).hexdigest(),
           "bytes": len(data), "estado": "", "segundos": "", "retorno": "", "detalle": "", "salida": ""}
    with tempfile.TemporaryDirectory(prefix="basic-corpus-") as td:
        sandbox = Path(td)
        work = sandbox / "A"
        # Preservar subdirectorios y archivos acompañantes (imagenes/sonidos/BAS incluidos).
        shutil.copytree(root, work, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        env = os.environ.copy()
        env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
        cmd = [python, "-m", "basic_cde", str(work / relative),
               "--mount-a", str(work), "--mount-b", str(work),
               "--max-instructions", str(max_instructions)]
        try:
            proc = subprocess.run(cmd, input="", text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, cwd=work, env=env, timeout=timeout)
            status, detail = classify(proc.returncode, proc.stderr, proc.stdout, False)
            row.update(estado=status, retorno=proc.returncode,
                       detalle=detail, salida=(proc.stdout + "\n" + proc.stderr)[-1200:])
        except subprocess.TimeoutExpired as exc:
            row.update(estado="TIEMPO_AGOTADO", retorno="timeout",
                       detalle=f"Supero {timeout:g} s; posible juego/espera/PAUSE", salida="")
        except (OSError, UnicodeError) as exc:
            row.update(estado="ERROR_EJECUTOR", retorno="", detalle=str(exc), salida="")
    row["segundos"] = round(time.monotonic() - start, 3)
    return row


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("corpus", type=Path, help="Directorio raiz con BAS y archivos acompanantes")
    p.add_argument("--out", type=Path, default=Path("informe-corpus"), help="Carpeta de informes")
    p.add_argument("--timeout", type=float, default=2.0, help="Segundos maximos por programa")
    p.add_argument("--max-instructions", type=int, default=12000)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--src", type=Path, default=Path(__file__).resolve().parents[1] / "src")
    args = p.parse_args()
    root = args.corpus.expanduser().resolve()
    if not root.is_dir():
        p.error(f"No existe el directorio {root}")
    programs = sorted((f for f in root.rglob("*") if f.is_file() and f.suffix.lower() == ".bas"),
                      key=lambda x: str(x).casefold())
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    print(f"Corpus: {root} | BAS: {len(programs)} | limite: {args.timeout:g}s / {args.max_instructions} instr")
    for n, program in enumerate(programs, 1):
        row = run_one(program, root, args.python, args.src.resolve(), args.timeout, args.max_instructions)
        rows.append(row)
        print(f"[{n:03}/{len(programs):03}] {row['estado']:<22} {row['programa']}", flush=True)
    with (out / "resultados.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(x["estado"] for x in rows)
    manifest = {"raiz": str(root), "total": len(rows), "estados": dict(counts),
                "criterio": "TERMINA no valida interfaz ni equivalencia con hardware; limites e INPUT no son fallas verificadas"}
    (out / "resumen.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out / "resumen.md").open("w", encoding="utf-8") as f:
        f.write("# Auditoria de corpus BASIC PicoCalc Linux\n\n")
        f.write(f"Programas encontrados: **{len(rows)}**. Las pruebas son headless y acotadas.\n\n")
        for key, count in counts.most_common():
            f.write(f"- {key}: {count}\n")
        f.write("\n## Casos que requieren investigacion\n\n")
        for x in rows:
            if x["estado"] != "TERMINA":
                f.write(f"- `{x['programa']}` — {x['estado']}: {x['detalle'].replace(chr(10), ' ')[:180]}\n")
        f.write("\n**Advertencia:** un programa que termina no esta necesariamente validado visualmente; "
                "uno que agota tiempo o instrucciones puede estar funcionando correctamente y esperando usuario.\n")
    print("Estados:", dict(counts), "| Informes:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
