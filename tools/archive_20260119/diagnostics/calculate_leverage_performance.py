"""
레버리지 성능 계산 (v1.0 - 2026-01-19)

지정가 주문 결과에 레버리지를 적용한 성능 계산
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

print(f"{'='*80}")
print(f"시장가 백테스트 (레버리지 1x)")
print(f"{'='*80}\n")

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

# 레버리지 배율 테스트
leverage_list = [1, 2, 3, 4, 5, 10]

print(f"{'='*80}")
print(f"지정가 주문 레버리지별 성능")
print(f"{'='*80}\n")

print(f"기본 정보:")
print(f"  총 거래: {len(limit_trades):,}개")
print(f"  체결률: {len(limit_trades)/len(market_trades)*100:.1f}%")
print(f"  1x 거래당 PnL: {sum(t['pnl'] for t in limit_trades)/len(limit_trades):.3f}%\n")

print(f"{'='*80}")
print(f"레버리지별 성능 비교")
print(f"{'='*80}")
print(f"{'레버리지':>8} {'거래당 PnL':>12} {'총 PnL':>12} {'MDD':>10} {'Sharpe':>10} {'PF':>10} {'안전성':>10}")
print(f"{'-'*80}")

results = []

for lev in leverage_list:
    # 레버리지 적용
    leveraged_trades = []
    for trade in limit_trades:
        lev_trade = trade.copy()
        lev_trade['pnl'] = trade['pnl'] * lev
        leveraged_trades.append(lev_trade)

    # 메트릭 계산
    metrics = calculate_backtest_metrics(leveraged_trades, leverage=1, capital=100.0)

    # 안전성 판단
    if metrics['mdd'] < 5:
        safety = "매우 안전"
    elif metrics['mdd'] < 10:
        safety = "안전"
    elif metrics['mdd'] < 20:
        safety = "주의"
    else:
        safety = "위험"

    print(f"{lev:>8}x {metrics['avg_pnl']:>11.3f}% {metrics['total_pnl']:>11.2f}% {metrics['mdd']:>9.2f}% {metrics['sharpe_ratio']:>10.2f} {metrics['profit_factor']:>10.2f} {safety:>10}")

    results.append({
        'leverage': lev,
        'avg_pnl': metrics['avg_pnl'],
        'total_pnl': metrics['total_pnl'],
        'mdd': metrics['mdd'],
        'sharpe': metrics['sharpe_ratio'],
        'pf': metrics['profit_factor'],
        'safety': safety
    })

print(f"{'='*80}\n")

# 5배 레버리지 상세
lev5 = results[4]  # 5배
print(f"{'='*80}")
print(f"5배 레버리지 상세 분석")
print(f"{'='*80}\n")

print(f"수익률:")
print(f"  거래당 PnL: {lev5['avg_pnl']:.3f}% (1x의 5배)")
print(f"  총 PnL: {lev5['total_pnl']:,.2f}%")
print(f"  연간 복리 성장률(CAGR): {lev5['total_pnl']/5.8:.1f}% (5.8년 기준)\n")

print(f"리스크:")
print(f"  MDD: {lev5['mdd']:.2f}%")
print(f"  안전성: {lev5['safety']}\n")

print(f"효율성:")
print(f"  Sharpe Ratio: {lev5['sharpe']:.2f}")
print(f"  Profit Factor: {lev5['pf']:.2f}\n")

# 초기 자본 100만원 기준
initial_capital = 1_000_000
final_capital_5x = initial_capital * (1 + lev5['total_pnl'] / 100)

print(f"실전 시뮬레이션 (초기 자본 100만원):")
print(f"  5배 레버리지 최종 자본: {final_capital_5x:,.0f}원")
print(f"  순수익: {final_capital_5x - initial_capital:,.0f}원")
print(f"  배율: {final_capital_5x / initial_capital:.1f}배\n")

# 권장 레버리지
print(f"{'='*80}")
print(f"권장 레버리지")
print(f"{'='*80}\n")

# MDD 10% 이하인 최대 레버리지 찾기
max_safe_lev = 1
for r in results:
    if r['mdd'] < 10:
        max_safe_lev = r['leverage']

print(f"MDD 10% 기준 최대 레버리지: {max_safe_lev}x")
print(f"  MDD: {results[leverage_list.index(max_safe_lev)]['mdd']:.2f}%")
print(f"  총 PnL: {results[leverage_list.index(max_safe_lev)]['total_pnl']:,.2f}%")
print(f"  Sharpe: {results[leverage_list.index(max_safe_lev)]['sharpe']:.2f}\n")

# 보수적 권장 (MDD 5% 이하)
conservative_lev = 1
for r in results:
    if r['mdd'] < 5:
        conservative_lev = r['leverage']

print(f"보수적 권장 (MDD 5% 기준): {conservative_lev}x")
print(f"  MDD: {results[leverage_list.index(conservative_lev)]['mdd']:.2f}%")
print(f"  총 PnL: {results[leverage_list.index(conservative_lev)]['total_pnl']:,.2f}%")
print(f"  Sharpe: {results[leverage_list.index(conservative_lev)]['sharpe']:.2f}\n")

print(f"{'='*80}\n")
