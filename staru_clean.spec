# -*- mode: python ; coding: utf-8 -*-
"""
TwinStar Quantum EXE 빌드 스펙 파일
"""

import os

block_cipher = None
PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['GUI/staru_main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # GUI 리소스만 (py 파일은 자동 수집됨)
        ('GUI/assets', 'GUI/assets'),
        
        # 설정 템플릿
        ('config/presets', 'config/presets'),
        ('api_key_config_template.json', '.'),
        ('GUI/styles.qss', 'GUI'),  # [ADD] 스타일 파일
        
        # 다국어 파일
        ('locales/*.json', 'locales'),
        
        # 버전 파일
        ('version.txt', '.'),
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.sip',
        'pyqtgraph', 'yaml',
        
        # Data
        'pandas', 'pandas._libs', 'pandas._libs.tslibs',
        'numpy', 'numpy.core', 'pyarrow',
        
        # Trading APIs
        'pybit', 'pybit.unified_trading',
        'binance', 'binance.client', 'binance.enums',
        'ccxt',
        
        # Korean Exchanges
        'pyupbit', 'pybithumb',
        
        # DEX
        'lighter',
        
        # WebSocket
        'websocket', 'websocket._core', 'websockets',
        
        # HTTP & Utils
        'requests', 'urllib3', 'aiohttp',
        'cryptography', 'cryptography.fernet',
        'cryptography.hazmat.primitives.ciphers.aead',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.backends',
        
        # TA
        'ta', 'pandas_ta',
        
        # Plotting
        'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_qt5agg',
        
        # Telegram
        'telegram', 'telegram.ext',
        
        # 표준 라이브러리
        'json', 'pathlib', 'queue', 'collections',
        'datetime', 'logging', 'logging.handlers',
        'hashlib', 'uuid', 'platform', 'threading', 'time', 'os', 'sys',
        
        # 인코딩
        'encodings', 'encodings.utf_8', 'encodings.cp949', 'encodings.euc_kr',
        
        # 프로젝트 모듈 (루트)
        'paths', 'utils.preset_manager',
        'license_manager', 'secure_storage', 'state_storage', 'trade_storage',
        'core.crypto_payment',
        'trade_history', 'telegram_notifier', 'indicator_generator',
        'exchanges.exchange_manager', 'smc_utils', 'system_doctor', 'error_guide',
        'bot_status', 'trading_safety', 'user_guide',
        
        # core 모듈
        'core', 'core.strategy_core', 'core.unified_bot', 
        'core.optimizer', 'core.license_guard', 'core.updater', 'core.__init__',
        'core.multi_optimizer', 'core.multi_backtest', 'core.dual_track_trader',
        'core.preset_health',
        
        
        # 거래소 모듈
        'exchanges', 'exchanges.base_exchange', 'exchanges.bybit_exchange',
        'exchanges.binance_exchange', 'exchanges.bitget_exchange',
        'exchanges.okx_exchange', 'exchanges.bingx_exchange',
        'exchanges.upbit_exchange', 'exchanges.bithumb_exchange',
        'exchanges.lighter_exchange', 'exchanges.ccxt_exchange', 'exchanges.ws_handler',
        
        # GUI 모듈
        'GUI', 'GUI.styles', 'GUI.constants', 'GUI.crypto_manager',
        'GUI.login_dialog', 'GUI.payment_dialog', 'GUI.onboarding_dialog',
        'GUI.trading_dashboard', 'GUI.backtest_widget', 'GUI.history_widget',
        'GUI.settings_widget', 'GUI.data_collector_widget', 'GUI.optimization_widget',
        'GUI.exchange_selector_widget', 'GUI.backtest_result_widget', 'GUI.bot_status_widget',
        'GUI.cache_manager_widget', 'GUI.capital_management_widget', 'GUI.capital_manager',
        'GUI.chart_items', 'GUI.data_download_widget', 'GUI.data_loader', 'GUI.data_manager',
        'GUI.developer_mode_widget', 'GUI.enhanced_chart_widget', 'GUI.help_dialog',
        'GUI.help_widget', 'GUI.i18n', 'GUI.indicator_generator', 'GUI.live_trading_manager',
        'GUI.login', 'GUI.notification_manager', 'GUI.notification_widget', 'GUI.nowcast_widget',
        'GUI.pc_license_dialog', 'GUI.position_widget', 'GUI.register_dialog', 'GUI.security',
        'GUI.strategy_interface', 'GUI.strategy_selector_widget', 'GUI.symbol_cache',
        'GUI.telegram_settings_widget', 'GUI.trade_chart_dialog', 'GUI.trade_detail_popup',
        'GUI.trade_executor', 'GUI.websocket_manager', 'GUI.candle_aggregator', 'GUI.staru_main',
        'GUI.tier_popup', 'GUI.help_popup', 'GUI.glossary_popup', 'GUI.telegram_popup', 'GUI.update_popup',
        'GUI.multi_system_widget', 'GUI.utils.data_utils',
        'utils', 'utils.bot_data_utils',
        
        # pycryptodome (암호화)
        'Crypto', 'Crypto.Cipher', 'Crypto.Cipher.AES',
        'Crypto.Util', 'Crypto.Util.Padding',
        
        # strategies
        'strategies',
        'strategies.strategy_loader',
        'strategies.wm_pattern_strategy',
        'strategies.parameter_optimizer',
        'strategies.example_strategy',
        
        # locales (다국어)
        'locales', 'locales.lang_manager',
        
        # license
        'license_tiers',
        
        # 멀티 트레이더 (Phase 4)
        'core.multi_trader', 'core.multi_sniper',
        'utils.symbol_converter',
        'GUI.multi_session_popup', 'GUI.sniper_session_popup',
        
        # 누락된 모듈 추가 (2025-12-22)
        'core.auto_optimizer',
        'utils.time_utils',
        'utils.cache_cleaner',
        'utils.error_reporter',
        'utils.api_utils',
        'utils.data_utils',
        'utils.preset_manager',
        'utils.new_coin_detector',
        'exchanges.exchange_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'IPython', 'jupyter', 'pytest', 'test'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='TwinStar_Quantum',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='GUI/assets/icon.ico',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='TwinStar_Quantum',
)
