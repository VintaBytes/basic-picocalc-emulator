# Compatibility and known limitations

BASIC PicoCalc Emulator is a **desktop BASIC interpreter independently implemented in Python**, targeting a useful subset of PicoCalc's MMBasic/PicoMite behavior. It is not an RP2040/RP2350 CPU emulator and **does not execute the original PicoMite firmware**.

The project was developed using available documentation, code-level references where useful, regression tests and observations from a real PicoCalc. The main physical reference for compatibility work was a PicoCalc running **WebMite on RP2350A, MMBasic 6.00003**. Behavior may differ with other firmware versions or variants.

## What is available

- BASIC interpreter with common language constructs, numeric and string operations.
- Graphics, bitmap fonts and a virtual 320 × 320 pixel display.
- Virtual keyboard and several desktop PicoCalc layouts.
- A: and B: virtual drives, BASIC program load/run and chained RUN functionality.
- BASIC text editor and basic program interaction.
- Many MMBasic instructions implemented, with automated regression coverage.

These are capability categories, **not a promise that every command, argument or edge case is identical to firmware**.

## Important limitations

- Full MMBasic/PicoMite compatibility **has not been achieved or claimed**.
- Some graphics, timing, memory accounting, sound and file operations can differ from physical PicoCalc behavior.
- Hardware-dependent commands and access to real PicoCalc peripherals, GPIO, buses and firmware services are not replicated as physical hardware.
- The virtual A:/B: drives use host files and directories rather than emulating all SD/flash hardware semantics.
- No RP2350 instruction-set or PicoMite firmware emulation.
- Pre-release binaries are currently **Linux x86_64 only**. Windows and macOS are not tested or distributed.
- Programs written for other MMBasic editions or firmware versions may need features not yet implemented.

The program examples and tests included in this repository are not a comprehensive catalog of every MMBasic command. Passing automated tests is not proof of complete compatibility.

## Tested software and what we need from users

The author has successfully run the available set of BASIC programs used during development, including interactive and graphics examples. This is **practical testing on a finite set of programs**, not a claim that every third-party program will work.

If you find an incompatibility, please open a [GitHub issue](https://github.com/VintaBytes/basic-picocalc-emulator/issues/new) and attach a small reproducible BASIC example. Describe:

1. Your Linux distribution and emulator version.
2. Your reference PicoCalc hardware/firmware version (if tested on real hardware).
3. The BASIC source or a minimal snippet, plus any data files needed.
4. What happens on real PicoCalc (or what the relevant MMBasic documentation specifies).
5. What happens in the emulator; include the error text or a screenshot when useful.

Do not upload personal or copyrighted third-party programs without permission. We welcome bug reports, reproducible cases and contributions. We cannot promise fixes for every unsupported feature.

See [README](../README.md), [Building](BUILDING.md) and [Contributing / reporting bugs](CONTRIBUTING.md).
