# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

a = Analysis(
    ['Youtube.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Assets', 'Assets'),
        ('dist/ffmpeg', 'ffmpeg'),
        ('cookies.txt', '.')
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL.ImageTk',
        'PIL.Image',
        'yt_dlp',
        'requests'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Youtube',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Assets\\icon.ico'],
)
