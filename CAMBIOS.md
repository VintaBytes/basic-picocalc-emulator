# Public changelog / Historial público de versiones

This file summarizes the public releases of BASIC PicoCalc Emulator. Detailed
internal development diaries, research records and early experimental logs are
maintained separately from this repository.

Este archivo resume las versiones públicas de BASIC PicoCalc Emulator. Las
bitácoras internas de ingeniería, investigaciones y entregas experimentales
se conservan por separado.

## v0.3.10-dev.0 — 2026-11-23

**First public Linux x86_64 development pre-release.**
**Primera versión preliminar pública para Linux x86_64.**

- Independent Python-based MMBasic-compatible interpreter.
- Desktop PicoCalc interface with four photographic layouts, virtual LCD,
  keyboard and BASIC editor.
- Virtual drives, BASIC execution, graphics and a set of implemented
  MMBasic commands.
- Source code, reproducible regression tests and instructions in the public
  repository.
- AppImage with third-party licensing notices, checksum and automated
  checks during packaging.
- Actual compatibility remains partial and under development; not an
  emulation of the original firmware or RP2350 CPU.

**Download / Descarga:**
https://github.com/VintaBytes/basic-picocalc-emulator/releases/tag/v0.3.10-dev.0

**Known limitations / Limitaciones:**
[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)

## Development history / Desarrollo anterior

The 0.1.x, 0.2.x and 0.3.0–0.3.9 iterations established the interpreter,
virtual graphics/display, keyboard handling, file operations, language
compatibility, physical-device comparisons and GUI layouts.

Las iteraciones 0.1.x, 0.2.x y 0.3.0–0.3.9 permitieron implementar y probar
el intérprete, las funciones gráficas, teclado, archivos, compatibilidad con
MMBasic y distintas interfaces gráficas. Esas versiones eran entregas
internas de desarrollo, no releases públicos independientes.

Historical code changes can be inspected in Git history. No old instructions
for building from the previous monorepository are applicable to this
standalone project.
