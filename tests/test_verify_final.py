# test_verify_final.py - constants_test.py 기반 최종 검증

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# GUI 경로 추가
_gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'GUI')
if _gui_dir not in sys.path:
    sys.path.insert(0, _gui_dir)

from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS
import pandas as pd

# 데이터 로드
df_15m = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')

if 'timestamp' in df_15m.columns:
    if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    else:
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m = df_15m.set_index('timestamp')

df_1h = df_15m.resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
}).dropna().reset_index()
df_15m = df_15m.reset_index()

print(f"로드 데이터: 1h={len(df_1h)}개 ({len(df_1h)//24}일)")
print(f"테스트 파라미터:")
for k, v in DEFAULT_PARAMS.items():
    if k in ['macd_fast', 'macd_slow', 'macd_signal', 'ema_period', 'atr_mult', 'rsi_period']:
        print(f"  - {k}: {v}")

core = AlphaX7Core(use_mtf=True)
print("\n최종 검증 백테스트 실행 중...")

valid_keys = [
    'atr_mult', 'trail_start_r', 'trail_dist_r', 'pattern_tolerance', 
    'entry_validity_hours', 'pullback_rsi_long', 'pullback_rsi_short', 
    'max_adds', 'filter_tf', 'rsi_period', 'atr_period', 'macd_fast', 
    'macd_slow', 'macd_signal', 'ema_period', 'slippage'
]
params = {k: v for k, v in DEFAULT_PARAMS.items() if k in valid_keys}

trades = core.run_backtest(
    df_pattern=df_1h,
    df_entry=df_15m,
    **params
)

if trades:
    leverage = 3
    pnls = [float(str(t['pnl']).replace('%','')) * leverage for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    total = sum(pnls)
    
    equity, peak, max_dd = 100, 100, 0
    for p in pnls:
        equity *= (1 + p / 100)
        if equity > peak: peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd: max_dd = dd
    
    print("\n" + "=" * 50)
    print("최종 파라미터 검증 결과 (3x 레버리지)")
    print("=" * 50)
    print(f"거래 수: {len(trades)}")
    print(f"승률: {wins / len(trades) * 100:.1f}%")
    print(f"총 수익 (단순): {total:.0f}%")
    print(f"MDD: {max_dd:.1f}%")
    print("=" * 50)
    
    if max_dd <= 10:
        print("초안정적인 수익 확인 (MDD 10% 미만)")
    elif max_dd <= 20:
        print("안정적인 수익 확인 (MDD 20% 이하)")
else:
    print("거래 없음")
