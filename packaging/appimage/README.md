# AppImage — PicoCalc BASIC (Linux x86_64)

This directory contains the public build scripts for the standalone
[BASIC PicoCalc Emulator](../../README.md). The repository's current
AppImage release is published at:

https://github.com/VintaBytes/basic-picocalc-emulator/releases/tag/v0.3.10-dev.0

## Build locally

From the root of **this repository**:

```bash
bash packaging/appimage/build.sh
```

The resulting file is written to:

`dist/BASIC-PicoCalc-Emulator-0.3.10.dev0-x86_64.AppImage`

The script builds an isolated Python environment in `build/appimage/venv`,
uses PyInstaller and appimagetool, and does not modify an existing development
`.venv` or personal BASIC files.

Requirements: Linux x86_64, Python 3.10+, python3-venv, curl, coreutils and
an Internet connection. Some Linux distributions require additional Qt/XCB
runtime libraries.

```bash
chmod +x dist/BASIC-PicoCalc-Emulator-0.3.10.dev0-x86_64.AppImage
dist/BASIC-PicoCalc-Emulator-0.3.10.dev0-x86_64.AppImage
```

If FUSE is unavailable, use `APPIMAGE_EXTRACT_AND_RUN=1`.

## Automated release

`.github/workflows/publish-appimage.yml` runs the regression suite, builds
the Linux package, inspects the bundled license notices and absence of unused
Qt Virtual Keyboard components, generates the SHA-256 checksum, and publishes
the development AppImage to GitHub Releases.

The source package and license resources remain in this public repository.
The release binary contains license and attribution notices under
`usr/share/doc/basic-picocalc/`.

## Notes

This is a **development pre-release**, not a full PicoMite firmware emulator.
The runtime may depend on Linux graphics/ABI components. Only Linux x86_64 is
supported by this packaging process. See [Building guide](../../docs/BUILDING.md),
[Compatibility](../../docs/COMPATIBILITY.md) and
[Third-party notices](../../docs/THIRD_PARTY_NOTICES.md).

---

# Español

El constructor produce el AppImage para Linux x86_64 desde el **repositorio
independiente**, sin utilizar rutas del antiguo monorepositorio.

Para compilar, desde la raíz:

```bash
bash packaging/appimage/build.sh
```

El ejecutable queda en `dist/`. No modifica programas BASIC personales,
unidades virtuales ni el entorno `.venv` habitual. GitHub Actions también
construye, prueba y publica la versión preliminar, incluyendo el archivo
`SHA256SUMS`.

Los registros técnicos históricos y los procedimientos internos de desarrollo
no forman parte de esta guía pública.
