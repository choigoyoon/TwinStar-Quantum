"""
복리 레버리지 성능 계산 (v1.0 - 2026-01-19)

단리가 아닌 복리(재투자) 기준으로 레버리지 성능 계산
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics

# 올바른 파라미터
CORRECT_PARAMS = {
    'atr_mult': 1.25,
    'filter_tf': '4h',
    'trail_start_r': 0.4,
    'trail_dist_r': 0.05,
    'entry_validity_hours': 6.0,
    'leverage': 1,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7
}

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()

if dm.df_entry_full is None:
    raise ValueError("데이터가 비어 있습니다.")

df_15m = dm.df_entry_full.copy()

# 리샘플링
df_temp = df_15m.set_index('timestamp')
df_1h = df_temp.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()
df_1h.reset_index(inplace=True)

# 지표 추가
add_all_indicators(df_1h, inplace=True)

# 전략 초기화
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

# 시장가 백테스트
market_trades = strategy.run_backtest(
    df_pattern=df_1h,
    df_entry=df_1h,
    slippage=0.001,
    **CORRECT_PARAMS
)

# 지정가 체결 시뮬레이션
limit_offset = 0.00001  # 0.001%
limit_trades = []

for trade in market_trades:
    entry_idx = trade.get('entry_idx', 0)
    side = trade.get('type', 'Long')

    if entry_idx >= len(df_1h):
        continue

    entry_candle = df_1h.iloc[entry_idx]
    open_price = entry_candle['open']
    low = entry_candle['low']
    high = entry_candle['high']

    # 체결 여부 확인
    filled = False
    actual_entry = open_price

    if side == 'Long':
        limit_price = open_price * (1 - limit_offset)
        if low <= limit_price:
            filled = True
            actual_entry = limit_price
    else:  # Short
        limit_price = open_price * (1 + limit_offset)
        if high >= limit_price:
            filled = True
            actual_entry = limit_price

    if filled:
        adjusted_trade = trade.copy()
        original_entry = trade.get('entry_price', open_price)
        entry_diff_pct = (actual_entry - original_entry) / original_entry
        original_pnl = trade.get('pnl', 0)

        if side == 'Long':
            adjusted_pnl = original_pnl - (entry_diff_pct * 100)
        else:
            adjusted_pnl = original_pnl + (entry_diff_pct * 100)

        # 수수료 차이 반영 (0.27%)
        adjusted_pnl += 0.27
        adjusted_trade['pnl'] = adjusted_pnl
        adjusted_trade['entry_price'] = actual_entry
        limit_trades.append(adjusted_trade)

print(f"{'='*80}")
print(f"복리 레버리지 성능 계산")
print(f"{'='*80}\n")

print(f"기본 정보:")
print(f"  총 거래: {len(limit_trades):,}개")
print(f"  체결률: {len(limit_trades)/len(market_trades)*100:.1f}%\n")

# 레버리지별 복리 계산
leverage_list = [1, 2, 3, 4, 5, 10]

print(f"{'='*80}")
print(f"레버리지별 복리 성능")
print(f"{'='*80}")
print(f"{'레버리지':>8} {'거래당 PnL':>12} {'단리 합계':>12} {'복리 최종':>15} {'MDD':>10} {'Sharpe':>10}")
print(f"{'-'*80}")

results = []

for lev in leverage_list:
    # 복리 계산 (재투자)
    capital = 100.0
    equity_curve = [capital]
    peak = capital
    max_dd = 0

    # 오버플로우 방지: 1e100 제한
    overflow_flag = False

    for trade in limit_trades:
        if overflow_flag:
            break

        # 거래당 PnL에 레버리지 적용
        pnl_pct = trade['pnl'] * lev

        # 복리: 현재 자본에 비율 적용
        capital = capital * (1 + pnl_pct / 100)

        # 오버플로우 체크
        if capital > 1e100:
            overflow_flag = True
            capital = 1e100
            break

        equity_curve.append(capital)

        # MDD 계산
        if capital > peak:
            peak = capital
        drawdown = (peak - capital) / peak * 100
        if drawdown > max_dd:
            max_dd = drawdown

    # 단리 합계 (비교용)
    simple_total = sum(t['pnl'] * lev for t in limit_trades)

    # 복리 최종
    if overflow_flag:
        compound_return = float('inf')
        compound_return_str = "오버플로우 (>1e100)"
    else:
        compound_return = (capital - 100.0) / 100.0 * 100
        compound_return_str = f"{compound_return:,.2f}%"

    # 거래당 평균 (단리 기준)
    avg_pnl = simple_total / len(limit_trades)

    # Sharpe (단리 기준)
    pnls = [t['pnl'] * lev for t in limit_trades]
    import numpy as np
    if len(pnls) > 1:
        sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252 * 4) if np.std(pnls) > 0 else 0
    else:
        sharpe = 0

    # 안전성 판단
    if max_dd < 5:
        safety = "매우 안전"
    elif max_dd < 10:
        safety = "안전"
    elif max_dd < 20:
        safety = "주의"
    else:
        safety = "위험"

    # 출력 포맷
    if overflow_flag:
        print(f"{lev:>8}x {avg_pnl:>11.3f}% {simple_total:>11.2f}% {'오버플로우':>14} {max_dd:>9.2f}% {sharpe:>10.2f}")
    else:
        print(f"{lev:>8}x {avg_pnl:>11.3f}% {simple_total:>11.2f}% {compound_return:>14.2f}% {max_dd:>9.2f}% {sharpe:>10.2f}")

    results.append({
        'leverage': lev,
        'avg_pnl': avg_pnl,
        'simple_total': simple_total,
        'compound_return': compound_return,
        'final_capital': capital,
        'mdd': max_dd,
        'sharpe': sharpe,
        'safety': safety
    })

print(f"{'='*80}\n")

# 5배 레버리지 상세
lev5 = results[4]  # 5배
print(f"{'='*80}")
print(f"5배 레버리지 복리 상세 분석")
print(f"{'='*80}\n")

print(f"수익률:")
print(f"  거래당 PnL: {lev5['avg_pnl']:.3f}%")
print(f"  단리 합계: {lev5['simple_total']:,.2f}%")

if isinstance(lev5['compound_return'], float) and lev5['compound_return'] == float('inf'):
    print(f"  복리 최종: 오버플로우 (>1e100)")
    print(f"  최종 자본: >1e100 (천문학적 숫자)")
else:
    print(f"  복리 최종: {lev5['compound_return']:,.2f}%")
    print(f"  차이: {lev5['compound_return'] - lev5['simple_total']:+,.2f}%\n")

print(f"리스크:")
print(f"  MDD: {lev5['mdd']:.2f}%")
print(f"  안전성: {lev5['safety']}\n")

print(f"효율성:")
print(f"  Sharpe Ratio: {lev5['sharpe']:.2f}\n")

# 초기 자본 100만원 기준
initial_capital = 1_000_000

print(f"\n실전 시뮬레이션 (초기 자본 100만원):")
if isinstance(lev5['compound_return'], float) and lev5['compound_return'] == float('inf'):
    print(f"  복리는 천문학적 수치로 계산 불가")
    print(f"  (2,056번 거래에서 평균 6.26% 복리 = 1.0626^2056)")
else:
    final_capital_5x = lev5['final_capital'] / 100 * initial_capital
    print(f"  5배 레버리지 최종 자본: {final_capital_5x:,.0f}원")
    print(f"  순수익: {final_capital_5x - initial_capital:,.0f}원")
    print(f"  배율: {final_capital_5x / initial_capital:,.1f}배")
print()

print(f"{'='*80}")
print(f"단리 vs 복리 비교")
print(f"{'='*80}\n")

for idx, lev in enumerate([1, 2, 5, 10]):
    r = results[leverage_list.index(lev)]

    print(f"{lev}배 레버리지:")
    print(f"  단리: {r['simple_total']:,.2f}%")

    if isinstance(r['compound_return'], float) and r['compound_return'] == float('inf'):
        print(f"  복리: 오버플로우 (계산 불가)")
        print(f"  차이: 천문학적\n")
    else:
        diff = r['compound_return'] - r['simple_total']
        diff_pct = diff / r['simple_total'] * 100 if r['simple_total'] > 0 else 0
        print(f"  복리: {r['compound_return']:,.2f}%")
        print(f"  차이: {diff:+,.2f}% ({diff_pct:+.1f}%)\n")

print(f"{'='*80}")
print(f"권장 레버리지")
print(f"{'='*80}\n")

# MDD 10% 이하인 최대 레버리지 찾기
max_safe_lev = 1
for r in results:
    if r['mdd'] < 10:
        max_safe_lev = r['leverage']

print(f"MDD 10% 기준 최대 레버리지: {max_safe_lev}x")
r = results[leverage_list.index(max_safe_lev)]
print(f"  MDD: {r['mdd']:.2f}%")
print(f"  단리: {r['simple_total']:,.2f}%")

if isinstance(r['compound_return'], float) and r['compound_return'] == float('inf'):
    print(f"  복리: 오버플로우 (계산 불가)")
else:
    print(f"  복리: {r['compound_return']:,.2f}%")
    print(f"  100만원 → {r['final_capital']/100*1_000_000:,.0f}원 ({r['final_capital']/100:.1f}배)")
print()

# 보수적 권장 (MDD 5% 이하)
conservative_lev = 1
for r in results:
    if r['mdd'] < 5:
        conservative_lev = r['leverage']

print(f"보수적 권장 (MDD 5% 기준): {conservative_lev}x")
r = results[leverage_list.index(conservative_lev)]
print(f"  MDD: {r['mdd']:.2f}%")
print(f"  단리: {r['simple_total']:,.2f}%")

if isinstance(r['compound_return'], float) and r['compound_return'] == float('inf'):
    print(f"  복리: 오버플로우 (계산 불가)")
else:
    print(f"  복리: {r['compound_return']:,.2f}%")
    print(f"  100만원 → {r['final_capital']/100*1_000_000:,.0f}원 ({r['final_capital']/100:.1f}배)")
print()

print(f"{'='*80}\n")
