#!/usr/bin/env python3
"""Prepare redistribution notices and exclude unused Qt Virtual Keyboard binaries.

Runs inside the isolated AppImage build venv. Deliberately fails if the
required license material cannot be found; do not silently ship an
unattributed build.
"""
from __future__ import annotations

import importlib.metadata as metadata
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
appdir = Path(sys.argv[2]).resolve()
frozen = appdir / "usr/bin/basic-picocalc/_internal"
notices = appdir / "usr/share/doc/basic-picocalc"
licenses = notices / "licenses"
licenses.mkdir(parents=True, exist_ok=True)

# Qt Virtual Keyboard is a GPL-only add-on and is not used by our own
# PicoCalc keyboard. PyInstaller may collect it transitively along with Qt.
removed = []
# Match both filenames and parents (for Qt QML plugin directories).
# Delete from the deepest path outward to keep removal deterministic.
for item in sorted(frozen.rglob("*"), key=lambda p: len(p.parts), reverse=True):
    if "virtualkeyboard" not in str(item.relative_to(frozen)).lower():
        continue
    if not (item.is_file() or item.is_symlink()):
        continue
    removed.append(item.relative_to(appdir).as_posix())
    item.unlink()
for item in sorted(frozen.rglob("*"), key=lambda p: len(p.parts), reverse=True):
    if "virtualkeyboard" in str(item.relative_to(frozen)).lower() and item.is_dir():
        item.rmdir()

leftovers = [
    str(p) for p in frozen.rglob("*")
    if "virtualkeyboard" in str(p.relative_to(frozen)).lower()
]
if leftovers:
    raise SystemExit("Unused Qt Virtual Keyboard components remain: " + repr(leftovers))

# Preserve our license and notices, as well as the original PicoMite terms.
for source, target in (
    ("LICENSE", "LICENSE-MIT.txt"),
    ("docs/THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
    ("docs/licenses/PicoMite-V6.03.00-Version.h", "PicoMite-V6.03.00-Version.h"),
):
    src = root / source
    if not src.is_file():
        raise SystemExit(f"Required legal notice missing: {src}")
    shutil.copy2(src, notices / target)

# Copy the *actual installed wheel's* license files, not guessed versions.
# Preserve relative filenames to avoid collisions between LICENSES files.
required = ("PySide6_Essentials", "PySide6_Addons", "PySide6_Pdf", "shiboken6", "Pillow")
qt_wheels = {"PySide6_Essentials", "PySide6_Addons", "PySide6_Pdf", "shiboken6"}
manifest = [
    "# Third-party license payload",
    "",
    "Generated from the wheels installed in the isolated AppImage build environment.",
    "Qt wheel license texts are based on the SPDX License List canonical texts",
    "from https://github.com/spdx/license-list-data/tree/main/text.",
    "The packaged .so libraries remain under their respective third-party licenses.",
    "See THIRD_PARTY_NOTICES.md; the standalone Python project code is MIT.",
    "",
]
for name in required:
    dist = metadata.distribution(name)
    files = dist.files or []
    found = []
    for entry in files:
        parts = entry.parts
        basename = entry.name.lower()
        if ("licenses" in (p.lower() for p in parts)
                or basename.startswith(("license", "copying", "notice"))
                or basename in {"lgpl-3.0.txt", "gpl-3.0.txt"}):
            src = Path(dist.locate_file(entry))
            if src.is_file():
                dst = licenses / name / Path(*parts)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                found.append(str(dst.relative_to(notices)))
    # The upstream PySide6 Qt wheels do not always bundle copies of the
    # applicable license texts. Ship fixed, reviewed SPDX canonical texts
    # from our source tree rather than relying on remote build-time fetches.
    if name in qt_wheels:
        declared = dist.metadata.get("License-Expression", "")
        # Some upstream wheels omit License-Expression entirely; in that case
        # the canonical license texts included with this source distribution
        # remain authoritative. Reject only explicit incompatible declarations.
        if declared and "LGPL-3.0" not in declared and "LGPLv3" not in declared:
            raise SystemExit(f"Unexpected Qt wheel license expression for {name}: {declared!r}")
        for filename in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt", "GPL-2.0-only.txt"):
            src = root / "packaging/licenses" / filename
            if not src.is_file() or src.stat().st_size < 4000:
                raise SystemExit(f"Missing bundled SPDX license text: {src}")
            dst = licenses / name / "SPDX" / filename
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            found.append(str(dst.relative_to(notices)))
    if not found:
        raise SystemExit(
            f"No license texts found in installed distribution {name} {dist.version}; "
            "do not publish this binary until its legal material is supplied."
        )
    manifest.append(f"## {name} {dist.version}")
    manifest.append(f"Declared license expression: {dist.metadata.get('License-Expression', 'not specified')}")
    manifest.extend(f"- {p}" for p in sorted(found))
    manifest.append("")

manifest += [
    "## Replacing LGPL Qt libraries",
    "",
    "This AppImage uses shared Qt/PySide6 libraries (not statically linked into",
    "the application). Users may extract the AppImage with --appimage-extract,",
    "replace compatible shared libraries in squashfs-root/usr/bin/basic-picocalc/",
    "_internal/PySide6/Qt/lib/ and other relevant library locations, and invoke",
    "squashfs-root/AppRun to run with their replacements.",
    "The freely available source and build instructions for this application",
    "are in https://github.com/VintaBytes/basic-picocalc-emulator.",
    "Corresponding Qt/PySide6 source code is available from https://code.qt.io/",
    "and https://download.qt.io/ under the applicable open-source licenses.",
    "The license texts accompanying this release determine each library's terms.",
    "",
    "## AppImage runtime",
    "",
    "The AppImage type-2 runtime includes third-party software whose credits",
    "and license references can be displayed by executing the AppImage with",
    "--appimage-help. See https://github.com/AppImage/type2-runtime.",
    "",
    "## Excluded unused Qt GPL-only module",
    "",
    "Qt Virtual Keyboard plugin and libraries are excluded from this build.",
    "Removed paths:",
]
manifest.extend(f"- {p}" for p in sorted(removed))
(notices / "BUNDLED_LICENSES.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
print(f"Included licensing material for {len(required)} wheel distributions; "
      f"excluded {len(removed)} unused virtual keyboard files.")
