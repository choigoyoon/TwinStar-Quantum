# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 프로젝트 루트
PROJECT_DIR = os.getcwd()

# 데이터 파일 (아이콘, UI 리소스 등)
# 형식: (원본경로, 배포경로)
datas = [
    ('GUI/assets', 'GUI/assets'),
    ('config/presets/_default.json', 'config/presets'), # 기본 프리셋 포함
    # config 폴더 전체를 포함하지 않는 이유: 사용자 설정은 exe 밖에 있어야 함
]

# Hidden Imports (PyInstaller가 못 찾는 모듈 강제 포함)
hiddenimports = [
    'pandas', 
    'numpy', 
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'ccxt',
    'preset_manager',
    'crypto_manager',
    'exchange_manager',
    'optimizer',
    'strategy_core',
    'pybit',
    'requests',
]

a = Analysis(
    ['GUI/staru_main.py'],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='StarU_Bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 모드 (콘솔 숨김)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='GUI/assets/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StarU_Bot',
)
