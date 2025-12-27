# -*- mode: python ; coding: utf-8 -*-
"""
StarU EXE 빌드 스펙 파일 (최종 배포용)
- 모든 필수 모듈 hiddenimports 포함
- API 키, JSON 제외
- ccxt 수동 포함
"""
import os
import sys

block_cipher = None
PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))
CCXT_PATH = r"C:\Users\naver\AppData\Local\Programs\Python\Python311\Lib\site-packages\ccxt"

a = Analysis(
    ['GUI/staru_main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        ('GUI/assets/*', 'GUI/assets'),
        ('strategy_core.py', '.'),
        ('unified_bot.py', '.'),
        ('optimizer.py', '.'),
        ('preset_manager.py', '.'),
        ('license_manager.py', '.'),
        ('secure_storage.py', '.'),
        ('state_storage.py', '.'),
        ('trade_storage.py', '.'),
        ('trade_history.py', '.'),
        ('telegram_notifier.py', '.'),
        ('indicator_generator.py', '.'),
        ('smc_utils.py', '.'),
        ('paths.py', '.'),
        ('system_doctor.py', '.'),
        ('error_guide.py', '.'),
        ('exchanges/*.py', 'exchanges'),
        ('strategies/*.py', 'strategies'),
        ('GUI/*.py', 'GUI'),
        ('GUI/utils/*.py', 'GUI/utils'),
        (CCXT_PATH, 'ccxt'),
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui',
        'PyQt5.QtChart', 'PyQt5.sip', 'sip',
        # 데이터
        'pandas', 'pandas.core.ops.array_ops', 'numpy',
        'numpy.core._methods', 'numpy.lib.format',
        # 차트
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.figure',
        'matplotlib.backends.backend_qt5agg', 'matplotlib.backends.backend_agg',
        'pyqtgraph',  # [ADD]
        # 거래소
        'ccxt', 'ccxt.async_support', 'pybit',
        'websocket', 'websocket._core', 'websockets',
        # 네트워크
        'requests', 'urllib3', 'aiohttp', 'asyncio',
        'certifi', 'charset_normalizer', 'idna',
        'yarl',  # [ADD] aiohttp 의존
        # 암호화
        'cryptography', 'cryptography.fernet',
        'cryptography.hazmat', 'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.backends', 'cryptography.hazmat.backends.openssl',
        'cffi', 'pycparser',
        'OpenSSL', 'OpenSSL.crypto', 'OpenSSL.SSL',  # [ADD] pyOpenSSL
        # 기술적 분석
        'ta', 'ta.momentum', 'ta.trend', 'ta.volatility',
        # 파싱/직렬화
        'lark',  # [ADD]
        'marshmallow', 'marshmallow.fields',  # [ADD]
        # 기타
        'json', 'uuid', 'hashlib', 'base64',
        'threading', 'queue', 'logging', 'datetime',
        'dateutil', 'pytz', 'six',
        'typeguard', 'typing_extensions',  # [ADD]
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'notebook', 'jupyter', 'IPython',
        'scipy', 'pytest', 'pandas.tests', 'numpy.tests',
        # [FIX] 테스트/검증 파일 제외 (EXE에 불필요)
        'test_phase1', 'test_phase2', 'test_phase3', 'test_phase4',
        'test_wallet_safety', 'test_backtest', 'test_optimizer',
        'verify_all', 'verify_trading', 'verify_connections',
        'verify_license', 'verify_bot', 'verify_logic_alignment',
        'verify_opt_ui', 'bot_master', 'analyze_patterns',
        # [FIX] 분석 스크립트 제외 (Low Priority)
        'bounce_strength_analysis', 'candle_pattern_analysis',
        'double_bottom_failure_analysis', 'mtf_lh_analysis',
        'per_trade_analysis', 'plan_geometry_analysis',
        'simple_pattern_analysis', 'strategy_c_failure_analysis',
        'trendline_deep_analysis', 'true_bottom_analysis',
        'user_provided_analysis', 'analyze_imports',
    ],
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
    name='TwinStar_Quantum',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_ROOT, 'GUI', 'assets', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TwinStar_Quantum',
)
