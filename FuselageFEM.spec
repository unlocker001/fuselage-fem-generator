# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Fuselage FEM Generator by Massinissa Ben Djoudi.

One-file build. Bundles PySide6 with PyVista and VTK for the interactive 3D viewport.
"""

from PyInstaller.utils.hooks import collect_all

datas = [
    ('presets/*.json', 'presets'),
    ('icon.ico', '.'),
    ('icon.png', '.'),
]
binaries = []
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

# Pull in every submodule / data file / binary these packages need at runtime.
for _pkg in ('pyvista', 'pyvistaqt', 'vtkmodules'):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Only PySide6 may be bundled; PyInstaller aborts if a second Qt binding is
        # collected (matplotlib's Qt backend would otherwise pull PyQt5).
        'PyQt5',
        'PyQt6',
        'PySide2',
        'tkinter',
        'IPython',
        'jupyter',
        'scipy',
        'pandas',
        'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FuselageFEM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
