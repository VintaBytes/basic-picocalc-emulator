# Contributing and reporting compatibility issues

Thanks for helping improve BASIC PicoCalc Emulator!

## Bug reports

Please use [GitHub Issues](https://github.com/VintaBytes/basic-picocalc-emulator/issues). For interpreter compatibility issues, include a **small, standalone .BAS program** which demonstrates the difference, together with the exact input and expected and observed outputs.

Whenever possible, compare the same file on a real PicoCalc and note its MMBasic version. A test that fails only on the emulator is especially useful; a program that merely times out waiting for input is not necessarily a bug.

For graphics discrepancies, provide a screenshot from the emulator and, if available, a photo from the physical device. Note whether a command relies on peripherals or an extension specific to a PicoMite version.

Avoid posting credentials, personal file paths, private application code, or third-party software without redistribution rights.

## Contributions

Changes should target a narrowly defined issue, include an automated regression test where possible, and preserve existing behavior. Do not modify an original third-party BASIC program merely to make it pass: isolate the incompatibility and correct the interpreter when justified.

Before opening a pull request:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[gui,test]'
python -m pytest -q
```

The core interpreter lives in `src/basic_cde/`. Linux AppImage packaging is described in [Building](BUILDING.md).

The project's independently developed code is MIT-licensed. Third-party font data, images and bundled libraries have separate attribution and licensing requirements: see [Third-party notices](THIRD_PARTY_NOTICES.md).

This repository is the public standalone project. Internal research notes from the historical monorepository are not required for an issue or contribution.
