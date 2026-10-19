# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a one-folder Windows build.

Build from the repository root:

    pyinstaller packaging/desktop_pet.spec

The output is ``dist/DesktopPet/DesktopPet.exe``.  Only the assets that are
present in the repository are bundled: the CC0 placeholder character, the icon
and the font folder (no font is shipped).  Keep third-party character packs in
``%APPDATA%/DesktopPet/characters`` instead.
"""

from pathlib import Path

from kivy_deps import glew, sdl2
from PyInstaller.building.datastruct import Tree

ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "assets"), "assets"),
    ],
    hiddenimports=[
        "kivy.uix.popup",
        "kivy.uix.boxlayout",
        "kivy.uix.label",
        "kivy.uix.button",
        "kivy.uix.floatlayout",
        "tkinter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DesktopPet",
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
    icon=str(ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *[Tree(path) for path in (sdl2.dep_bins + glew.dep_bins)],
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DesktopPet",
)
