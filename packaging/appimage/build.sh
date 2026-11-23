#!/usr/bin/env bash
# Construye AppImage x86_64 a partir del proyecto; no modifica venv existente.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "ERROR: este constructor solo soporta Linux x86_64." >&2
  exit 2
fi
PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; assert sys.version_info >= (3,10)' >/dev/null 2>&1; then
  echo "ERROR: se necesita Python >= 3.10." >&2
  exit 2
fi
if ! command -v curl >/dev/null || ! command -v sha256sum >/dev/null; then
  echo "ERROR: instalar curl y coreutils." >&2
  exit 2
fi

BUILD_DIR="${BUILD_DIR:-$ROOT/build/appimage}"
DIST_DIR="$ROOT/dist"
VENV="$BUILD_DIR/venv"
APPDIR="$BUILD_DIR/BASIC-PicoCalc-Emulator.AppDir"
TOOL="$BUILD_DIR/appimagetool-x86_64.AppImage"
VERSION="$("$PYTHON" -c 'import pathlib,re; s=pathlib.Path("pyproject.toml").read_text(); print(re.search(r"(?m)^version = \"([^\"]+)\"",s).group(1))')"
OUTPUT="$DIST_DIR/BASIC-PicoCalc-Emulator-$VERSION-x86_64.AppImage"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

echo "== Entorno de compilacion aislado =="
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install '.[gui]' 'pyinstaller>=6,<7'

echo "== PyInstaller onedir =="
"$VENV/bin/python" -m PyInstaller \
  --noconfirm --clean --onedir \
  --name basic-picocalc \
  --distpath "$BUILD_DIR/pyinstaller-dist" \
  --workpath "$BUILD_DIR/pyinstaller-work" \
  --specpath "$BUILD_DIR" \
  --collect-data basic_cde \
  packaging/appimage/entry.py

echo "== Smoke test del binario congelado =="
"$BUILD_DIR/pyinstaller-dist/basic-picocalc/basic-picocalc" --help >/dev/null
# --version no forma parte del CLI. Comprobar --help y carga de la GUI mediante prueba manual.

echo "== Preparar AppDir =="
rm -rf -- "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a "$BUILD_DIR/pyinstaller-dist/basic-picocalc" "$APPDIR/usr/bin/basic-picocalc"
cp packaging/appimage/AppRun "$APPDIR/AppRun"
chmod 755 "$APPDIR/AppRun"
cp packaging/appimage/basic-picocalc.desktop "$APPDIR/basic-picocalc.desktop"
cp packaging/appimage/basic-picocalc.desktop "$APPDIR/usr/share/applications/basic-picocalc.desktop"

"$VENV/bin/python" - "$ROOT" "$APPDIR" <<'PY'
from pathlib import Path
from PIL import Image
import sys
root, appdir = map(Path, sys.argv[1:])
original = root / "src/basic_cde/gui/assets/picocalc-transparent.png"
with Image.open(original) as image:
    icon = Image.open(original).convert("RGBA")
    icon.thumbnail((256, 256), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    canvas.alpha_composite(icon, ((256-icon.width)//2, (256-icon.height)//2))
    location = appdir / "usr/share/icons/hicolor/256x256/apps/basic-picocalc.png"
    canvas.save(location)
    (appdir / "basic-picocalc.png").write_bytes(location.read_bytes())
PY

echo "== Auditar y anexar licencias de terceros =="
"$VENV/bin/python" packaging/appimage/prepare_licenses.py "$ROOT" "$APPDIR"

echo "== appimagetool =="
if [[ -n "${APPIMAGETOOL:-}" ]]; then
  TOOL="$APPIMAGETOOL"
elif [[ ! -f "$TOOL" ]]; then
  curl -fL --retry 3 \
    'https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage' \
    -o "$TOOL"
fi
chmod +x "$TOOL"
rm -f -- "$OUTPUT"
ARCH=x86_64 VERSION="$VERSION" APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"
echo "== Listo =="
sha256sum "$OUTPUT"
echo "$OUTPUT"
echo "Prueba: $OUTPUT --help"
echo "Prueba GUI: $OUTPUT"
