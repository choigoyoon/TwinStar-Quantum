"""Meta 결과로 백테스트 - 초간단 버전

Usage:
    python tools/test_meta_result.py
"""

import sys
sys.path.insert(0, '.')

import json
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics


# Meta 결과 로드
with open('presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json', 'r') as f:
    meta = json.load(f)

print("="*80)
print("Meta 최적화 결과 백테스트")
print("="*80)

# 데이터 로드
print("\n데이터 로드 중...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
dm.load_historical()

df = dm.df_entry_full.copy().set_index('timestamp')
df = df.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
df = df.reset_index()
df = add_all_indicators(df, inplace=False)

print(f"데이터: {len(df)}개 캔들")

# Quick 파라미터 (시작값)
p = meta['param_ranges_by_mode']
params = {
    'atr_mult': p['atr_mult']['quick'][0],
    'filter_tf': p['filter_tf']['quick'][0],
    'trail_start_r': p['trail_start_r']['quick'][0],
    'trail_dist_r': p['trail_dist_r']['quick'][0],
    'entry_validity_hours': p['entry_validity_hours']['quick'][0]
}

print("\n파라미터:")
for k, v in params.items():
    print(f"  {k}: {v}")

# 백테스트
print("\n백테스트 실행...")
strategy = AlphaX7Core(use_mtf=True)
trades = strategy.run_backtest(
    df_pattern=df, df_entry=df,
    slippage=0.0005,
    pattern_tolerance=0.05,
    enable_pullback=False,
    **params
)

# 결과
if trades:
    m = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    print("\n" + "="*80)
    print("결과")
    print("="*80)
    print(f"Sharpe Ratio      : {m['sharpe_ratio']:.2f}")
    print(f"Win Rate          : {m['win_rate']:.1f}%")
    print(f"MDD               : {m['mdd']:.2f}%")
    print(f"Profit Factor     : {m['profit_factor']:.2f}")
    print(f"Total Trades      : {m['total_trades']}")
    print(f"Total PnL         : {m['total_pnl']:.2f}%")
    print("="*80)
else:
    print("\n거래 없음")
