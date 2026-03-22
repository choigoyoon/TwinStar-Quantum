"""Meta 결과 파라미터 비교

Quick 모드의 시작값 vs 끝값 비교

Usage:
    python tools/compare_meta_params.py
"""

import sys
sys.path.insert(0, '.')

import json
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics


def test_params(df, params, name):
    """파라미터 테스트"""
    strategy = AlphaX7Core(use_mtf=True)
    trades = strategy.run_backtest(
        df_pattern=df, df_entry=df,
        slippage=0.0005, pattern_tolerance=0.05, enable_pullback=False,
        **params
    )

    if trades:
        m = calculate_backtest_metrics(trades, leverage=1, capital=100.0)
        print(f"\n{name}")
        print("-"*60)
        for k, v in params.items():
            print(f"  {k:22s}: {v}")
        print()
        print(f"  Sharpe     : {m['sharpe_ratio']:7.2f}")
        print(f"  Win Rate   : {m['win_rate']:6.1f}%")
        print(f"  MDD        : {m['mdd']:6.2f}%")
        print(f"  PF         : {m['profit_factor']:7.2f}")
        print(f"  Trades     : {m['total_trades']:6d}")
        return m
    else:
        print(f"\n{name}: 거래 없음")
        return None


# Meta 로드
with open('presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json', 'r') as f:
    meta = json.load(f)

print("="*80)
print("Meta 파라미터 비교")
print("="*80)

# 데이터 로드
print("\n데이터 로드...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
dm.load_historical()

if dm.df_entry_full is None:
    raise ValueError("데이터 로드 실패")

df = dm.df_entry_full.copy().set_index('timestamp')
df = df.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna().reset_index()
df = add_all_indicators(df, inplace=False)
print(f"데이터: {len(df)}개")

# Quick 파라미터
p = meta['param_ranges_by_mode']

# 1. 보수적 (시작값)
params1 = {
    'atr_mult': p['atr_mult']['quick'][0],
    'filter_tf': p['filter_tf']['quick'][0],
    'trail_start_r': p['trail_start_r']['quick'][0],
    'trail_dist_r': p['trail_dist_r']['quick'][0],
    'entry_validity_hours': p['entry_validity_hours']['quick'][0]
}

# 2. 공격적 (끝값)
params2 = {
    'atr_mult': p['atr_mult']['quick'][1],
    'filter_tf': p['filter_tf']['quick'][1],
    'trail_start_r': p['trail_start_r']['quick'][1],
    'trail_dist_r': p['trail_dist_r']['quick'][1],
    'entry_validity_hours': p['entry_validity_hours']['quick'][1]
}

# 3. 혼합 (시작 atr + 끝 trail)
params3 = {
    'atr_mult': p['atr_mult']['quick'][0],
    'filter_tf': p['filter_tf']['quick'][0],
    'trail_start_r': p['trail_start_r']['quick'][1],
    'trail_dist_r': p['trail_dist_r']['quick'][1],
    'entry_validity_hours': p['entry_validity_hours']['quick'][0]
}

# 테스트
print("\n" + "="*80)
m1 = test_params(df, params1, "[1] 보수적 (타이트 손절 + 빠른 익절)")
m2 = test_params(df, params2, "[2] 공격적 (넓은 손절 + 늦은 익절)")
m3 = test_params(df, params3, "[3] 혼합 (타이트 손절 + 늦은 익절)")

# 비교
print("\n" + "="*80)
print("비교 결과")
print("="*80)
print(f"{'':12s} {'[1] 보수적':>12s} {'[2] 공격적':>12s} {'[3] 혼합':>12s}")
print("-"*60)

if m1 and m2 and m3:
    print(f"{'Sharpe':12s} {m1['sharpe_ratio']:12.2f} {m2['sharpe_ratio']:12.2f} {m3['sharpe_ratio']:12.2f}")
    print(f"{'Win Rate':12s} {m1['win_rate']:11.1f}% {m2['win_rate']:11.1f}% {m3['win_rate']:11.1f}%")
    print(f"{'MDD':12s} {m1['mdd']:11.2f}% {m2['mdd']:11.2f}% {m3['mdd']:11.2f}%")
    print(f"{'PF':12s} {m1['profit_factor']:12.2f} {m2['profit_factor']:12.2f} {m3['profit_factor']:12.2f}")
    print(f"{'Trades':12s} {m1['total_trades']:12d} {m2['total_trades']:12d} {m3['total_trades']:12d}")

    # 승자
    sharpes = [m1['sharpe_ratio'], m2['sharpe_ratio'], m3['sharpe_ratio']]
    winner = sharpes.index(max(sharpes)) + 1
    print(f"\n최고 성능: [{winner}]")

print("="*80)
