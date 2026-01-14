# Full Pipeline Consistency Verification
# 수집 → 최적화 → 백테스트 → 매매 전체 검증

from pathlib import Path
import json
import pandas as pd

base = Path(__file__).parent
preset_path = base / 'config/presets/bybit_btcusdt_optimized.json'

print("=" * 70)
print("FULL PIPELINE VERIFICATION")
print("=" * 70)

# ========== 1. DATA COLLECTION ==========
print("\n[1] DATA COLLECTION")
cache_dir = base / 'data' / 'cache'
if not cache_dir.exists():
    cache_dir = base / 'cache'

if cache_dir.exists():
    parquet_files = list(cache_dir.glob('*.parquet'))
    btc_files = [f for f in parquet_files if 'btcusdt' in f.name.lower()]
    
    for f in btc_files[:3]:
        df = pd.read_parquet(f)
        print(f"  {f.name}: {len(df):,} rows")
        if len(df) > 0:
            # Date range
            if 'timestamp' in df.columns:
                ts = pd.to_datetime(df['timestamp'])
                print(f"    Range: {ts.min()} ~ {ts.max()}")
else:
    print("  ERROR: Cache directory not found!")

# ========== 2. OPTIMIZATION (JSON GENERATION) ==========
print("\n[2] OPTIMIZATION / JSON CHECK")
if preset_path.exists():
    preset = json.loads(preset_path.read_text(encoding='utf-8'))
    params = preset.get('params', {})
    result = preset.get('_result', {})
    
    print(f"  Preset: {preset_path.name}")
    print(f"  Trades: {result.get('trades', '?')}, WinRate: {result.get('win_rate', '?')}%")
    
    # RSI 값 체크
    rsi_long = params.get('pullback_rsi_long', 'N/A')
    rsi_short = params.get('pullback_rsi_short', 'N/A')
    print(f"  RSI: Long<{rsi_long}, Short>{rsi_short}")
    
    # 필수 파라미터 체크
    required = ['atr_mult', 'trail_start_r', 'trail_dist_r', 'filter_tf', 'entry_tf']
    missing = [k for k in required if k not in params]
    if missing:
        print(f"  WARNING: Missing params: {missing}")
    else:
        print(f"  OK: All required params present")
else:
    print(f"  ERROR: Preset not found: {preset_path}")

# ========== 3. BACKTEST CONSISTENCY ==========
print("\n[3] BACKTEST CONSISTENCY")
try:
    # strategy_core 로드 테스트
    import sys
    sys.path.insert(0, str(base))
    sys.path.insert(0, str(base / 'core'))
    
    from core.strategy_core import AlphaX7Core, ACTIVE_PARAMS, DEFAULT_PARAMS
    
    print(f"  ACTIVE_PARAMS source check:")
    print(f"    pullback_rsi_long: {ACTIVE_PARAMS.get('pullback_rsi_long', 'N/A')}")
    print(f"    pullback_rsi_short: {ACTIVE_PARAMS.get('pullback_rsi_short', 'N/A')}")
    
    # 프리셋 값과 비교
    if preset_path.exists():
        p_long = params.get('pullback_rsi_long')
        p_short = params.get('pullback_rsi_short')
        a_long = ACTIVE_PARAMS.get('pullback_rsi_long')
        a_short = ACTIVE_PARAMS.get('pullback_rsi_short')
        
        if p_long == a_long and p_short == a_short:
            print(f"  OK: Preset matches ACTIVE_PARAMS")
        else:
            print(f"  WARNING: Preset ({p_long}/{p_short}) != ACTIVE ({a_long}/{a_short})")
except Exception as e:
    print(f"  ERROR: {e}")

# ========== 4. LIVE TRADING PARAM LOADING ==========
print("\n[4] LIVE TRADING PARAM LOADING")
try:
    from utils.preset_manager import get_backtest_params, load_strategy_params
    
    # 1. load_strategy_params (config.json)
    config = load_strategy_params()
    print(f"  config.json RSI: Long<{config.get('pullback_rsi_long', 'N/A')}, Short>{config.get('pullback_rsi_short', 'N/A')}")
    
    # 2. get_backtest_params (preset)
    preset_name = "bybit_btcusdt_optimized"
    bp = get_backtest_params(preset_name)
    print(f"  preset RSI: Long<{bp.get('pullback_rsi_long', 'N/A')}, Short>{bp.get('pullback_rsi_short', 'N/A')}")
    
except Exception as e:
    print(f"  ERROR: {e}")

# ========== 5. DATA GAP CHECK ==========
print("\n[5] DATA GAP CHECK (Entry TF)")
try:
    entry_file = cache_dir / 'bybit_btcusdt_15m.parquet'
    if entry_file.exists():
        df = pd.read_parquet(entry_file)
        if 'timestamp' in df.columns:
            ts = pd.to_datetime(df['timestamp'])
            df_sorted = df.sort_values('timestamp')
            
            # Gap detection
            ts_sorted = pd.to_datetime(df_sorted['timestamp'])
            diffs = ts_sorted.diff()
            expected = pd.Timedelta(minutes=15)
            gaps = diffs[diffs > expected * 2]  # 30분 이상 갭
            
            if len(gaps) > 0:
                print(f"  WARNING: {len(gaps)} gaps detected (>30min)")
                print(f"    Largest gap: {gaps.max()}")
            else:
                print(f"  OK: No significant gaps")
                
            # Latest data freshness
            latest = ts_sorted.max()
            from datetime import datetime
            age = datetime.now() - latest.to_pydatetime()
            if age.total_seconds() < 3600:
                print(f"  OK: Data is fresh ({age.seconds//60}min old)")
            else:
                print(f"  WARNING: Data is stale ({age.total_seconds()//3600:.0f}h old)")
    else:
        print(f"  ERROR: Entry file not found: {entry_file}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
