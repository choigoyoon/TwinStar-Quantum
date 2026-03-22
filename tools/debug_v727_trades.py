"""v7.27 최적 파라미터 거래 횟수 디버그

test_adaptive_range_v2.py와 동일한 방식으로 백테스트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.metrics import calculate_backtest_metrics
import pandas as pd

# v7.27 최적 파라미터 (CSV 1위)
optimal_params = {
    'atr_mult': 1.438,
    'filter_tf': '4h',
    'entry_validity_hours': 48,
    'trail_start_r': 0.4,
    'trail_dist_r': 0.022,
    'leverage': 1,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7,
    'tolerance': 0.15,
    'use_adx_filter': False,
}

# 데이터 로드
print("데이터 로드...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
success = dm.load_historical()

if not success or dm.df_entry_full is None:
    print("데이터 로드 실패")
    sys.exit(1)

# 15m → 1h 리샘플링
df_15m = dm.df_entry_full.copy()

if 'timestamp' not in df_15m.columns:
    df_15m.reset_index(inplace=True)

df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
df_temp = df_15m.set_index('timestamp')

df = df_temp.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df.reset_index(inplace=True)

# 2020-01-01 이후
df = df[df['timestamp'] >= '2020-01-01'].copy()

print(f"데이터: {len(df):,}개 1h 캔들")

# 백테스트 (test_adaptive_range_v2.py와 동일)
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

TOTAL_COST = 0.0002  # v7.27과 동일
backtest_params = {k: v for k, v in optimal_params.items()
                  if k not in ['slippage', 'fee']}

print("\n백테스트 실행 (slippage=0.0002)...")
trades = strategy.run_backtest(
    df_pattern=df,
    df_entry=df,
    slippage=TOTAL_COST,
    **backtest_params
)

if isinstance(trades, tuple):
    trades = trades[0]

print(f"거래 횟수: {len(trades):,}회")

if len(trades) >= 10:
    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)
    print(f"\nSharpe: {metrics['sharpe_ratio']:.2f}")
    print(f"승률: {metrics['win_rate']:.1f}%")
    print(f"MDD: {metrics['mdd']:.2f}%")
    print(f"PF: {metrics['profit_factor']:.2f}")
