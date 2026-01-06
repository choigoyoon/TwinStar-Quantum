"""
verify_mdd.py - MDD 계산 검증 스크립트
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from core.strategy_core import AlphaX7Core, calculate_mdd, calculate_backtest_metrics

# 데이터 로드
df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df = df.set_index('timestamp')
df_1h = df.resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 
    'close': 'last', 'volume': 'sum'
}).dropna().reset_index()

# 백테스트 파라미터
params = {
    'atr_mult': 1.25,
    'trail_dist_r': 0.1,
    'pullback_rsi_long': 35,
    'pullback_rsi_short': 65,
    'entry_validity_hours': 6,
}

# 백테스트 실행
core = AlphaX7Core(use_mtf=True)
trades = core.run_backtest(df_1h, df_1h, **params)

# 메트릭 계산
metrics = calculate_backtest_metrics(trades)

print("=== MDD Calculation Added ===")
print(f"MDD: {metrics['max_drawdown']:.2f}%")
print(f"Return: {metrics['total_return']:.2f}%")
print(f"Trades: {metrics['trade_count']}")
print(f"WinRate: {metrics['win_rate']:.1f}%")
print(f"PF: {metrics['profit_factor']:.2f}")
print(f"Sharpe: {metrics['sharpe_ratio']:.2f}")

if metrics['max_drawdown'] > 0:
    optimal_lev = 20 / metrics['max_drawdown']
    print(f"Optimal Leverage (20% target MDD): {optimal_lev:.1f}x")
