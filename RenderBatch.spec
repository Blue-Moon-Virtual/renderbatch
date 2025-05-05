# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

block_cipher = None

# Get the path to tkinterdnd2 package
tkinterdnd2_path = os.path.dirname(os.path.abspath(__import__('tkinterdnd2').__file__))

# Collect all necessary files
tkdnd_binaries = collect_dynamic_libs('tkinterdnd2')
tkdnd_data = collect_data_files('tkinterdnd2')

# Add assets directory with correct structure
assets_data = [
    ('assets/logo_header.png', 'assets'),
    ('assets/logo_button.png', 'assets'),
    ('assets/logo_app_icon.png', 'assets'),
    ('assets/logo_char.png', 'assets')
]

a = Analysis(
    ['src/RenderBatch.py'],
    pathex=[],
    binaries=tkdnd_binaries,
    datas=tkdnd_data + assets_data,
    hiddenimports=['tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RenderBatch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo_app_icon.png'  # Add application icon
) 