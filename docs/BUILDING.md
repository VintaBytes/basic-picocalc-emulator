# Building BASIC PicoCalc Emulator

BASIC PicoCalc Emulator is an independent MMBasic-compatible
desktop environment for Linux. It does not execute the original firmware.

This document describes development, testing and AppImage
generation from the project source tree.

## Requirements

- Linux
- Python 3.10 or newer
- Python venv and pip
- Git
- curl and coreutils for AppImage generation

The AppImage builder currently targets Linux x86_64.

## Development installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[gui,test]'
```

## Running the emulator

```bash
basic-picocalc
```

Alternatively:

```bash
python -m basic_cde
```

## Running the tests

```bash
python -m pytest -q
```

Some tests may be skipped when optional components or
platform capabilities are unavailable.

## Building the AppImage

The provided builder creates an isolated environment
and installs the packaging dependencies.

```bash
bash packaging/appimage/build.sh
```

The generated package is written to:

    dist/BASIC-PicoCalc-Emulator-<version>-x86_64.AppImage

The builder uses PyInstaller and appimagetool.

PyInstaller is installed in a separate build environment;
it is not required in the regular development environment.

## Reproducibility

The project currently specifies minimum dependency versions.

Consequently, separate AppImage builds may incorporate
different compatible dependency releases.

A dependency lock or equivalent version-pinning mechanism
is planned for reproducible release builds.

## Third-party components

The project uses PySide6, Pillow and other components
with their own applicable licenses.

The graphical interface also includes image assets, and
the emulator includes ROM bitmap fonts originating from
PicoMite.

See THIRD_PARTY_NOTICES.md for provenance and licensing
information.

## Published development release

A Linux x86_64 **development pre-release** is available at
https://github.com/VintaBytes/basic-picocalc-emulator/releases/tag/v0.3.10-dev.0.

The public GitHub Actions workflow runs regression tests, builds the
Linux AppImage and checks legal notices and the absence of unused Qt Virtual
Keyboard components when the packaging workflow changes on `main`.
**Regular pushes do not upload or replace GitHub Releases.**

A new release must be explicitly initiated using `workflow_dispatch` after
updating the workflow's version/tag information for the new version. The
publish step refuses to overwrite an existing release tag or assets.
`SHA256SUMS` is generated from that specific build and attached to the
new release. Local builds may contain different compatible versions of
dependencies and are not guaranteed to have the same checksum.

This automated check is not a substitute for reviewing licenses of
dependencies in future versions.

## AppImage: bundled licensing material

The AppImage build copies the project's MIT license and PicoMite notices,
plus available license texts from the installed Python wheels, into
`usr/share/doc/basic-picocalc/` inside the AppImage. Some Qt/PySide6
wheels omit the texts; the builder supplies canonical LGPL/GPL texts from
`packaging/licenses/` (SPDX License List), and stops if required notices
are unavailable. A generated `BUNDLED_LICENSES.md` inventory records the
bundled material and installed dependency versions.

PyInstaller sometimes collects Qt Virtual Keyboard, a GPL-only Qt add-on,
even though BASIC PicoCalc Emulator has its own virtual keyboard. The builder
removes unused Virtual Keyboard binaries before packaging. This must be
rechecked on every rebuild.

For an AppImage produced by this builder, check the files without executing
the emulator:

```bash
./dist/BASIC-PicoCalc-Emulator-0.3.10.dev0-x86_64.AppImage --appimage-extract
find squashfs-root/usr/share/doc/basic-picocalc -type f
find squashfs-root/usr/bin/basic-picocalc -iname '*virtualkeyboard*'
```

The second `find` should list licensing files; the third should have no
output. Remove the generated `squashfs-root` directory afterward if desired.

The LGPL-covered shared libraries are dynamically loaded. The extracted
AppImage provides a way to replace compatible Qt shared libraries for testing
and modification; see `BUNDLED_LICENSES.md` in the image. If any additional
bundled dependency has obligations beyond those documented here, investigate
and satisfy those before binary publication. The build procedure does not
constitute legal certification.
