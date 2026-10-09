# -*- mode: python ; coding: utf-8 -*-

import sys
import os

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = [
    ('Assets', 'Assets')
]
datas += collect_data_files('customtkinter')

# Include ffmpeg folder if present in build environment
for ffmpeg_path in ['ffmpeg', 'dist/ffmpeg']:
    if os.path.isdir(ffmpeg_path):
        datas.append((ffmpeg_path, 'ffmpeg'))
        break

# Include cookies.txt only if present in working directory
if os.path.isfile('cookies.txt'):
    datas.append(('cookies.txt', '.'))

a = Analysis(
    ['Youtube.py'],
    pathex=[],
    binaries=[],
    datas=datas,
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
    icon=[os.path.join('Assets', 'icon.ico')],
)
