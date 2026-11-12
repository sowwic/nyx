# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec of Nyx: the editor and the CLI executables, for every platform.

Build it with `uv run python scripts/build.py build-app`, which also makes the icon file
in build/icons. Output is dist/nyx.app on macOS, the dist/nyx folder elsewhere.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH)
IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

version_file = ROOT / "VERSION"
app_version = version_file.read_text().strip() if version_file.exists() else "0.0.0"

# Plugins are found by scanning the package directories for `nyx_plugin.py`, so
# the sources of the stdlib and the builtin plugins (and all QML) have to be on
# disk next to the frozen modules. The modules themselves stay importable from
# the archive through the hidden imports.
datas = [
    (str(ROOT / "VERSION"), "."),
    (str(ROOT / "src/nyx/stdlib"), "nyx/stdlib"),
    (str(ROOT / "src/nyx/plugins"), "nyx/plugins"),
    (str(ROOT / "src/nyx/editor/qml"), "nyx/editor/qml"),
]
hiddenimports = collect_submodules("nyx")

# On macOS the icon belongs to the BUNDLE, on Windows to the executables.
if IS_MACOS:
    bundle_icon = str(ROOT / "build/icons/nyx.icns")
    exe_icon = None
elif IS_WINDOWS:
    bundle_icon = None
    exe_icon = str(ROOT / "build/icons/nyx.ico")
else:
    bundle_icon = exe_icon = None


def analyze(script):
    return Analysis(
        [str(ROOT / script)],
        pathex=[str(ROOT / "src")],
        binaries=[],
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        optimize=0,
    )


editor_analysis = analyze("src/nyx/__main__.py")
run_stage_analysis = analyze("src/nyx/run_stage_entry.py")

editor_pyz = PYZ(editor_analysis.pure)
run_stage_pyz = PYZ(run_stage_analysis.pure)

# Windowed executable: opens the editor, or runs `nyx stage run <path>` headless.
editor_exe = EXE(
    editor_pyz,
    editor_analysis.scripts,
    [],
    exclude_binaries=True,
    name="nyx",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

# Console executable, the counterpart of the `nyx-run-stage` script.
run_stage_exe = EXE(
    run_stage_pyz,
    run_stage_analysis.scripts,
    [],
    exclude_binaries=True,
    name="nyx-run-stage",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

coll = COLLECT(
    editor_exe,
    run_stage_exe,
    editor_analysis.binaries + run_stage_analysis.binaries,
    editor_analysis.datas + run_stage_analysis.datas,
    strip=False,
    upx=False,
    name="nyx",
)

if IS_MACOS:
    app = BUNDLE(
        coll,
        name="nyx.app",
        icon=bundle_icon,
        bundle_identifier=None,
        info_plist={
            "CFBundleName": "Nyx",
            "CFBundleDisplayName": "Nyx",
            "CFBundleShortVersionString": app_version,
            "CFBundleVersion": app_version,
            "NSHighResolutionCapable": True,
            # BUNDLE takes `console` from the last EXE, the console nyx-run-stage, and
            # would mark the app background-only: no Dock icon, no menu bar.
            "LSBackgroundOnly": False,
        },
    )
