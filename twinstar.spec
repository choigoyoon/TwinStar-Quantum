# -*- mode: python ; coding: utf-8 -*-
"""
TwinStar Quantum EXE 빌드 스펙 파일 (v1.7.1 최적화)
"""

import os

block_cipher = None
PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['GUI/staru_main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # GUI 리소스 (필수)
        ('GUI/assets', 'GUI/assets'),
        ('GUI/styles.qss', 'GUI'),
        ('GUI/styles', 'GUI/styles'),
        
        # Config (필수 정의 파일만, 민감 정보 제외)
        ('config/parameters.py', 'config'),
        ('config/settings.json', 'config'), 
        
        # Locales (다국어)
        ('locales', 'locales'),
        
        # Version & Meta
        ('version.txt', '.'),
        ('version.json', '.'),
        
        # Strategies (전략 로더)
        ('strategies', 'strategies'),
    ],
    hiddenimports=[
        # PyQt5
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.sip', 'PyQt5.QtChart', 'PyQt5.QtWebEngineWidgets',
        
        # Core Modules (Explicit)
        'core', 'core.strategy_core', 'core.auto_scanner', 'core.optimizer', 
        'core.batch_optimizer', 'core.batch_verifier', 'core.preset_health',
        'core.multi_symbol_backtest', 'core.multi_optimizer', 'core.updater',
        
        # Strategies
        'strategies', 'strategies.strategy_loader',
        
        # Exchange Adapters
        'exchanges', 'exchanges.binance_exchange', 'exchanges.bybit_exchange', 
        'exchanges.okx_exchange', 'exchanges.bitget_exchange', 'exchanges.upbit_exchange',
        
        # Utils
        'utils', 'utils.indicators', 'utils.logger', 'utils.preset_manager',
        
        # External Deps
        'ccxt', 'pandas', 'numpy', 'requests', 'cryptography', 'psutil', 'plotly',
        
        # GUI Package
        'GUI',
        'GUI.login', 'GUI.login_dialog', 'GUI.multi_session_popup', 'GUI.multi_system_widget',
        'GUI.notification_manager', 'GUI.notification_widget', 'GUI.nowcast_widget',
        'GUI.onboarding_dialog', 'GUI.optimization_widget', 'GUI.payment_dialog',
        'GUI.pc_license_dialog', 'GUI.position_widget', 'GUI.register_dialog', 'GUI.security',
        'GUI.settings_widget', 'GUI.sniper_session_popup', 'GUI.staru_main',
        'GUI.strategy_interface', 'GUI.strategy_selector_widget', 'GUI.styles', 'GUI.symbol_cache',
        'GUI.telegram_popup', 'GUI.telegram_settings_widget', 'GUI.tier_popup',
        'GUI.trade_chart_dialog', 'GUI.trade_detail_popup', 'GUI.trade_executor',
        'GUI.trading_dashboard', 'GUI.update_popup', 'GUI.websocket_manager',
        'GUI.test_history_widget', 'GUI.verify_all_modules',
        'GUI.styles.fonts', 'GUI.styles.theme', 'GUI.styles.elegant_theme', 
        'GUI.styles.premium_theme', 'GUI.styles.vivid_theme',
        'GUI.trading_dashboard_v2', 'GUI.trading_dashboard_v3',
        'GUI.test_history_widget', 'GUI.verify_all_modules',
        'GUI.data_collector_widget', 'GUI.backtest_widget', 'GUI.history_widget',
        'GUI.auto_pipeline_widget', 'GUI.backtest_result_widget',
        'GUI.capital_management_widget', 'GUI.dashboard_widgets',
        'GUI.single_trade_widget', 'GUI.multi_trade_widget', 'GUI.trading_tab_widget',
        'GUI.trade_history_widget', 'GUI.result_widget',
        
        # GUI Subpackages
        'GUI.components', 'GUI.components.bot_control_card', 'GUI.components.collapsible',
        'GUI.components.interactive_chart', 'GUI.components.market_status',
        'GUI.components.position_table', 'GUI.components.status_card', 'GUI.components.workers',
        'GUI.components.trade_panel',
        'GUI.pages', 'GUI.pages.step1_backtest', 'GUI.pages.step2_optimize',
        'GUI.pages.step3_trade', 'GUI.pages.step4_monitor', 'GUI.pages.step5_results',
        'GUI.dashboard', 'GUI.dashboard.multi_explorer',
        'GUI.styles.theme',
        
        # ========== core 모듈 (17) ==========
        'core', 'core.__init__',
        'core.auto_optimizer', 'core.batch_optimizer', 'core.chart_matcher', 'core.crypto_payment',
        'core.dual_track_trader', 'core.license_guard', 'core.multi_backtest',
        'core.multi_optimizer', 'core.multi_sniper', 'core.multi_symbol_backtest', 'core.multi_trader',
        'core.optimizer', 'core.preset_health', 'core.strategy_core',
        'core.bot_state', 'core.data_manager', 'core.optimization_logic',
        'core.order_executor', 'core.position_manager', 'core.signal_processor',
        'core.unified_bot', 'core.updater', 'core.capital_manager', 'core.trade_common', 'core.pnl_tracker',
        
        # ========== exchanges 모듈 (13) ==========
        'exchanges', 'exchanges.__init__',
        'exchanges.base_exchange', 'exchanges.binance_exchange', 'exchanges.bingx_exchange',
        'exchanges.bitget_exchange', 'exchanges.bithumb_exchange', 'exchanges.bybit_exchange',
        'exchanges.ccxt_exchange', 'exchanges.exchange_manager', 'exchanges.lighter_exchange',
        'exchanges.okx_exchange', 'exchanges.upbit_exchange', 'exchanges.ws_handler',
        
        # ========== storage 모듈 (5) ==========
        'storage', 'storage.__init__',
        'storage.secure_storage', 'storage.state_storage',
        'storage.trade_history', 'storage.trade_storage',
        
        # ========== utils 모듈 (14) ==========
        'utils', 'utils.__init__',
        'utils.api_utils', 'utils.bot_data_utils', 'utils.cache_cleaner',
        'utils.chart_profiler', 'utils.data_downloader', 'utils.data_utils',
        'utils.error_reporter', 'utils.helpers', 'utils.indicators', 'utils.new_coin_detector',
        'utils.preset_manager', 'utils.preset_storage', 'utils.symbol_converter',
        'utils.time_utils',
        
        # ========== strategies 모듈 (8) ==========
        'strategies', 'strategies.__init__',
        'strategies.common', 'strategies.common.backtest_engine', 'strategies.common.strategy_interface',
        'strategies.example_strategy', 'strategies.parameter_optimizer',
        'strategies.strategy_loader', 'strategies.wm_pattern_strategy',
        
        # ========== 루트 모듈 (필수) ==========
        'paths', 'license_manager', 'license_tiers',
        'telegram_notifier', 'indicator_generator', 'smc_utils',
        'error_guide', 'system_doctor', 'trading_safety', 'user_guide', 'bot_status',
        
        # ========== 외부 라이브러리 ==========
        # 데이터/분석
        'pandas', 'pandas._libs', 'pandas._libs.tslibs', 'pandas_ta',
        'numpy', 'numpy.core',
        'ta', 'sklearn', 'scipy',
        
        # 거래소 API
        'ccxt', 'pybit', 'pybit.unified_trading',
        'binance', 'binance.client', 'binance.enums',
        'pyupbit', 'pybithumb', 'lighter',
        
        # 네트워크
        'requests', 'urllib3', 'aiohttp', 'websocket', 'websocket._core', 'websockets',
        
        # 암호화
        'cryptography', 'cryptography.fernet',
        'cryptography.hazmat.backends', 'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.kdf.pbkdf2', 'cryptography.hazmat.primitives.ciphers.aead',
        'Crypto', 'Crypto.Cipher', 'Crypto.Cipher.AES', 'Crypto.Util', 'Crypto.Util.Padding',
        'OpenSSL',
        
        # 차트/시각화
        'matplotlib', 'matplotlib.backends.backend_qt5agg', 'matplotlib.pyplot',
        'pyqtgraph',
        
        # 유틸리티
        'json', 'yaml', 'hashlib', 'uuid', 'datetime', 'threading', 'queue', 'logging',
        'pathlib', 'encodings', 'encodings.utf_8', 'encodings.cp949',
        
        # GUI 신규 누락 모듈
        'GUI.bot_status_widget', 'GUI.candle_aggregator', 'GUI.capital_config',
        'GUI.capital_manager', 'GUI.chart_items', 'GUI.constants',
        'GUI.crypto_manager', 'GUI.data_download_widget', 'GUI.data_loader',
        'GUI.data_manager', 'GUI.debug_dashboard', 'GUI.developer_mode_widget',
        'GUI.enhanced_chart_widget', 'GUI.exchange_selector_widget',
        'GUI.glossary_popup', 'GUI.help_dialog', 'GUI.help_popup',
        'GUI.help_widget', 'GUI.i18n', 'GUI.indicator_generator',
        'GUI.legacy_styles', 'GUI.live_trading_manager',
        
        # Core & Utils 누락
        'core.async_scanner', 'core.unified_backtest',
        'utils.crypto', 'utils.health_check', 'utils.retry',
        'utils.state_manager', 'utils.updater', 'utils.validators',
        'strategies.base_strategy',
        'locales', 'locales.lang_manager',
        'config.parameters',

        # 데이터베이스
        'sqlalchemy', 'sqlalchemy.sql.default_comparator', 'sqlite3', 'orjson',
        
        # 기타
        'telegram', 'telegram.ext', 'dotenv', 'dataclasses',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'IPython', 'jupyter', 'pytest', 'test',
        '_backup_2025', 'dist', 'build', 'node_modules', '.venv',
        '*.log', '*.parquet', '.env',
        'tools', 'tools.*', 'backups', 'backups.*',
        'add_t_import', 'append_binance_ws', 'apply_hotfixes',
        'cleanup_project', 'collect_btc_data', 'compare_live_bt',
    ],
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
    console=False,
    icon='GUI/assets/icon.ico',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='TwinStar_Quantum',
)
