# test_verify_optimal.py - 최적 파라미터 검증 테스트

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.strategy_core import AlphaX7Core
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

OPTIMAL_PARAMS = {
    'macd_fast': 8,
    'macd_slow': 32,
    'macd_signal': 7,
    'ema_period': 10,
    'atr_mult': 2.0,
    'atr_period': 14,
    'rsi_period': 21,
    'trail_start_r': 0.8,
    'trail_dist_r': 0.5,
    'pullback_rsi_long': 45,
    'pullback_rsi_short': 55,
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 48,
    'filter_tf': '2h',
}

core = AlphaX7Core(use_mtf=True)
print("\n최적 파라미터로 백테스트 실행 중...")

trades = core.run_backtest(
    df_pattern=df_1h,
    df_entry=df_15m,
    **OPTIMAL_PARAMS
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
    print("최적 파라미터 검증 결과 (3x 레버리지)")
    print("=" * 50)
    print(f"거래 수: {len(trades)}")
    print(f"승률: {wins / len(trades) * 100:.1f}%")
    print(f"총 수익 (단순): {total:.0f}%")
    print(f"MDD: {max_dd:.1f}%")
    print("=" * 50)
    
    target_met = total >= 6000 and wins / len(trades) >= 0.85 and max_dd <= 15
    if target_met:
        print("목표 달성! (수익 6000%+, 승률 85%+, MDD 15%-)")
    else:
        print("목표 미달 (파라미터 확인 필요)")
else:
    print("거래 없음")
