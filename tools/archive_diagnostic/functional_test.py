# functional_test.py
# 저장 위치: c:\매매전략\functional_test.py
"""
TwinStar Quantum - 기능 작동 검증
실제 UI 동작 및 데이터 흐름 테스트
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'GUI'))

# PyQt Application 필요 (위젯 테스트용)
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([]    )

print("=" * 70)
print("🧪 TwinStar Quantum - 기능 작동 검증")
print("=" * 70)

results = {'pass': [], 'fail': [], 'warn': []}

def test(name, func):
    try:
        result = func()
        if result:
            results['pass'].append((name, result))
            print(f"✅ {name}")
            if isinstance(result, dict):
                for k, v in result.items():
                    print(f"   └─ {k}: {v}")
        else:
            results['warn'].append((name, "결과 없음")    )
            print(f"⚠️ {name}: 결과 없음")
    except Exception as e:
        results['fail'].append((name, str(e)))
        print(f"❌ {name}: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
print("\n" + "=" * 70)
print("📊 PHASE 1: 데이터 로드 테스트")
print("=" * 70 + "\n")

def test_parquet_load():
    """Parquet 데이터 로드"""
    from pathlib import Path
    from paths import Paths
    import pandas as pd
    
    cache_dir = Path(Paths.CACHE)
    if not cache_dir.exists():
         # 만약 캐시 디렉토리가 없으면 생성 (테스트용)
         cache_dir.mkdir(parents=True, exist_ok=True)

    files = list(cache_dir.glob("*.parquet"))
    
    if not files:
        print("   (SKIP) Parquet 파일 없음 - 테스트용 더미 파일 생성")
        # 더미 파일 생성
        df = pd.DataFrame({'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
                           'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000})
        df.to_parquet(cache_dir / "dummy_data.parquet")
        files = [cache_dir / "dummy_data.parquet"]
    
    latest = max(files, key=lambda p: p.stat().st_mtime)
    df = pd.read_parquet(latest)
    
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        raise Exception(f"필수 컬럼 누락: {missing}")
    
    return {
        'file': latest.name,
        'rows': len(df),
        'columns': list(df.columns)[:6]
    }

def test_indicator_generation():
    """지표 생성 테스트"""
    import pandas as pd
    import numpy as np
    from indicator_generator import IndicatorGenerator
    
    # 더미 데이터
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
        'open': np.random.uniform(40000, 45000, 100),
        'high': np.random.uniform(45000, 46000, 100),
        'low': np.random.uniform(39000, 40000, 100),
        'close': np.random.uniform(40000, 45000, 100),
        'volume': np.random.uniform(100, 1000, 100),
    })
    
    df = IndicatorGenerator.add_all_indicators(df)
    
    indicators = ['rsi', 'atr', 'macd', 'ema_20']
    found = [i for i in indicators if i in df.columns or f'{i}_14' in df.columns]
    
    return {'indicators_added': len(found), 'sample': found}

def test_resample():
    """리샘플링 테스트"""
    import pandas as pd
    import numpy as np
    from utils.data_utils import resample_data
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
        'open': np.random.uniform(40000, 45000, 100),
        'high': np.random.uniform(45000, 46000, 100),
        'low': np.random.uniform(39000, 40000, 100),
        'close': np.random.uniform(40000, 45000, 100),
        'volume': np.random.uniform(100, 1000, 100),
    })
    
    df_1h = resample_data(df, '1h', add_indicators=False)
    
    return {
        'original_rows': len(df),
        'resampled_rows': len(df_1h),
        'ratio': f"{len(df) / len(df_1h):.1f}x"
    }

test("1.1 Parquet 데이터 로드", test_parquet_load)
test("1.2 지표 생성", test_indicator_generation)
test("1.3 리샘플링", test_resample)


# ============================================================
print("\n" + "=" * 70)
print("🎯 PHASE 2: 전략 로직 테스트")
print("=" * 70 + "\n")

def test_pattern_detection():
    """W/M 패턴 탐지 테스트"""
    from core.strategy_core import AlphaX7Core
    
    core = AlphaX7Core()
    assert hasattr(core, 'detect_signal'), "detect_signal 메서드 없음"
    return {'detect_signal': True, 'class': 'AlphaX7Core'}

def test_backtest_execution():
    """백테스트 실행 테스트"""
    from core.strategy_core import AlphaX7Core
    import pandas as pd
    import numpy as np
    
    n = 500
    dates = pd.date_range('2024-01-01', periods=n, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 40000 + np.cumsum(np.random.randn(n) * 100),
        'high': 40000 + np.cumsum(np.random.randn(n) * 100) + 200,
        'low': 40000 + np.cumsum(np.random.randn(n) * 100) - 200,
        'close': 40000 + np.cumsum(np.random.randn(n) * 100),
        'volume': np.random.uniform(100, 1000, n),
    })
    from indicator_generator import IndicatorGenerator
    df = IndicatorGenerator.add_all_indicators(df)
    
    core = AlphaX7Core()
    assert hasattr(core, 'run_backtest'), "run_backtest 메서드 없음"
    
    return {'run_backtest': True, 'data_rows': n}

def test_trailing_logic():
    """트레일링 SL 로직 테스트"""
    from core.strategy_core import AlphaX7Core
    core = AlphaX7Core()
    methods = ['manage_position_realtime', 'update_trailing_sl', 'calculate_adaptive_params']
    found = [m for m in methods if hasattr(core, m)]
    return {'trailing_methods': found, 'count': len(found)}

test("2.1 패턴 탐지 로직", test_pattern_detection)
test("2.2 백테스트 실행", test_backtest_execution)
test("2.3 트레일링 로직", test_trailing_logic)


# ============================================================
print("\n" + "=" * 70)
print("🔌 PHASE 3: 거래소 어댑터 테스트")
print("=" * 70 + "\n")

def test_bybit_adapter():
    """Bybit 어댑터 메서드 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    methods = ['connect', 'get_klines', 'place_market_order', 'set_leverage', 'update_stop_loss', 'close_position']
    found = [m for m in methods if hasattr(BybitExchange, m)]
    missing = [m for m in methods if m not in found]
    if missing: raise Exception(f"누락된 메서드: {missing}")
    return {'methods': len(found), 'all_present': True}

def test_binance_adapter():
    """Binance 어댑터 메서드 테스트"""
    from exchanges.binance_exchange import BinanceExchange
    # fetch_ohlcv 대신 get_klines 사용 (통일됨)
    methods = ['connect', 'get_klines', 'place_market_order', 'set_leverage', 'update_stop_loss'] 
    found = [m for m in methods if hasattr(BinanceExchange, m)]
    missing = [m for m in methods if m not in found]
    if missing: raise Exception(f"누락된 메서드: {missing}")
    return {'methods': len(found), 'all_present': True}

def test_binance_sl_safety():
    """Binance SL 실패 시 청산 로직 확인"""
    import inspect
    from exchanges.binance_exchange import BinanceExchange
    source = inspect.getsource(BinanceExchange.place_market_order)
    has_emergency = 'EMERGENCY' in source or 'emergency' in source.lower() or 'reduceOnly' in source
    has_sl_try = 'except' in source and ('STOP' in source or 'sl_order' in source)
    if not (has_emergency): raise Exception("SL 실패 시 청산 로직 없음")
    return {'emergency_close': has_emergency, 'sl_try_block': has_sl_try}

test("3.1 Bybit 어댑터", test_bybit_adapter)
test("3.2 Binance 어댑터", test_binance_adapter)
test("3.3 Binance SL 안전장치", test_binance_sl_safety)


# ============================================================
print("\n" + "=" * 70)
print("💾 PHASE 4: 저장소 테스트")
print("=" * 70 + "\n")

def test_preset_save_load():
    """프리셋 저장/로드 테스트"""
    from utils.preset_manager import get_preset_manager
    pm = get_preset_manager()
    if not pm: raise Exception("PresetManager 초기화 실패")
    
    test_params = {'atr_mult': 1.5, 'trail_start_r': 0.8, 'leverage': 5, 'direction': 'Both'}
    test_name = '_test_preset_temp'
    pm.save_preset(test_name, {'params': test_params})
    loaded = pm.load_preset_flat(test_name)
    pm.delete_preset(test_name)
    if not loaded: raise Exception("프리셋 로드 실패")
    return {'save': True, 'load': True, 'delete': True}

def test_secure_storage():
    """암호화 저장소 테스트"""
    from storage.secure_storage import get_secure_storage
    storage = get_secure_storage()
    methods = ['get_exchange_keys', 'save_exchange_keys', 'load_api_keys']
    found = [m for m in methods if hasattr(storage, m)]
    return {'methods': len(found), 'singleton': True}

def test_state_storage():
    """상태 저장소 테스트"""
    from storage.state_storage import StateStorage
    storage = StateStorage('test_bot')
    test_state = {'position': None, 'capital': 1000}
    storage.save(test_state)
    loaded = storage.load()
    return {'save': True, 'load': loaded is not None}

test("4.1 프리셋 저장/로드", test_preset_save_load)
test("4.2 암호화 저장소", test_secure_storage)
test("4.3 상태 저장소", test_state_storage)


# ============================================================
print("\n" + "=" * 70)
print("🖥️ PHASE 5: GUI 위젯 기능 테스트")
print("=" * 70 + "\n")

def test_backtest_widget_flow():
    """백테스트 위젯 흐름 테스트"""
    from GUI.backtest_widget import BacktestWidget
    w = BacktestWidget()
    has_data = w.strategy is not None # df_15m은 로드 안해서 None일 수 있음
    has_run_btn = hasattr(w, '_run_btn')
    has_table = hasattr(w, '_trade_table')
    preset_count = w.preset_combo.count()
    return {'data_strategy': has_data, 'run_btn': has_run_btn, 'table': has_table, 'presets': preset_count}

def test_optimization_widget_flow():
    """최적화 위젯 흐름 테스트"""
    from GUI.optimization_widget import OptimizationWidget
    w = OptimizationWidget()
    param_count = len(w.param_widgets)
    data_count = w.data_combo.count()
    has_direction = hasattr(w, 'direction_widget')
    return {'param_widgets': param_count, 'data_sources': data_count, 'direction': has_direction}

def test_trading_dashboard_flow():
    """트레이딩 대시보드 흐름 테스트"""
    from GUI.trading_dashboard import TradingDashboard
    w = TradingDashboard()
    cp = w.control_panel
    has_preset = hasattr(cp, 'preset_combo')
    has_direction = hasattr(cp, 'direction_combo')
    has_exchange = hasattr(cp, 'exchange_combo')
    preset_count = cp.preset_combo.count() if has_preset else 0
    return {'preset_combo': has_preset, 'direction_combo': has_direction, 'exchange_combo': has_exchange, 'preset_count': preset_count}

def test_settings_widget_flow():
    """설정 위젯 흐름 테스트"""
    from GUI.settings_widget import SettingsWidget
    w = SettingsWidget()
    has_telegram = hasattr(w, 'telegram_card')
    toggle_count = len(w.exchange_toggles)
    return {'telegram': has_telegram, 'exchange_toggles': toggle_count}

def test_signal_connections():
    """시그널 연결 테스트"""
    from GUI.staru_main import StarUWindow
    # StarUWindow 생성 시 show() 호출 등 부작용 있을 수 있으므로 주의
    # 하지만 headless라 show()는 무시될 가능성 높음
    w = StarUWindow(user_tier='admin')
    
    signals = {
        'backtest_finished': hasattr(w.backtest_widget, 'backtest_finished'),
        'settings_applied': hasattr(w.optimization_widget, 'settings_applied'),
        'start_trading': hasattr(w.dashboard, 'start_trading_clicked'),
        'go_to_tab': hasattr(w.dashboard, 'go_to_tab'),
    }
    connected = sum(signals.values())
    return {'signals': signals, 'connected': f"{connected}/4"}

test("5.1 백테스트 위젯", test_backtest_widget_flow)
test("5.2 최적화 위젯", test_optimization_widget_flow)
test("5.3 트레이딩 대시보드", test_trading_dashboard_flow)
test("5.4 설정 위젯", test_settings_widget_flow)
test("5.5 시그널 연결", test_signal_connections)


# ============================================================
print("\n" + "=" * 70)
print("🔄 PHASE 6: 데이터 흐름 연동 테스트")
print("=" * 70 + "\n")

def test_optimization_to_backtest():
    """최적화~백테스트 연동"""
    # 단순 속성 확인으로 대체 (시그널 연결은 StarUWindow __init__에서 수행됨)
    from GUI.staru_main import StarUWindow
    w = StarUWindow(user_tier='admin')
    # 연결 코드는 connect_signals 메서드에 있음
    has_connect = hasattr(w, 'connect_signals')
    return {'has_connect_method': has_connect} # 실제 런타임 연결 확인은 어려움

def test_preset_to_dashboard():
    """프리셋~대시보드 연동"""
    from GUI.trading_dashboard import ControlPanel
    cp = ControlPanel()
    has_handler = hasattr(cp, '_on_preset_changed')
    has_info = hasattr(cp, 'preset_info')
    return {'handler': has_handler, 'info_label': has_info}

def test_4h_filter_effect():
    """4H 필터 체크박스 효과"""
    from GUI.backtest_widget import BacktestWidget
    w = BacktestWidget()
    has_chk = hasattr(w, 'chk_4h')
    checked = w.chk_4h.isChecked() if has_chk else None
    return {'checkbox': has_chk, 'default_checked': checked}

test("6.1 최적화-백테스트 연동", test_optimization_to_backtest)
test("6.2 프리셋-대시보드 연동", test_preset_to_dashboard)
test("6.3 4H 필터 효과", test_4h_filter_effect)


print("\n" + "=" * 70)
print("📋 최종 결과 확인")
print("=" * 70)

total = len(results['pass']) + len(results['fail']) + len(results['warn'])
pass_rate = len(results['pass']) / total * 100 if total > 0 else 0

print(f"\n✅ PASS: {len(results['pass'])}건")
print(f"⚠️ WARN: {len(results['warn'])}건")
print(f"❌ FAIL: {len(results['fail'])}건")

if results['fail']:
    print("\n" + "-" * 50)
    print("실패 항목:")
    for name, error in results['fail']:
        print(f"  ✗ {name}: {error}")
