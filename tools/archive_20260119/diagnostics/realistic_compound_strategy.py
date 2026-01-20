"""
현실적 복리 성장 전략 (v1.0 - 2026-01-19)

단계별 복리 → 단리 전환 시나리오
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators

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
print(f"현실적 복리 성장 전략 (5배 레버리지)")
print(f"{'='*80}\n")

# 시나리오 설정
leverage = 5
initial_capital = 1_000_000  # 100만원
thresholds = [
    (10_000_000, "1천만원"),      # 10배
    (50_000_000, "5천만원"),      # 50배
    (100_000_000, "1억원"),       # 100배
    (500_000_000, "5억원"),       # 500배
    (1_000_000_000, "10억원"),    # 1000배
    (float('inf'), "무제한")
]

print(f"초기 자본: {initial_capital:,}원")
print(f"레버리지: {leverage}x")
print(f"총 거래: {len(limit_trades):,}개\n")

print(f"{'='*80}")
print(f"복리 → 단리 전환 시나리오")
print(f"{'='*80}\n")

for threshold, name in thresholds:
    capital = initial_capital
    compound_phase_trades = 0
    simple_phase_trades = 0
    simple_profit = 0
    switched = False

    for i, trade in enumerate(limit_trades):
        pnl_pct = trade['pnl'] * leverage

        if capital < threshold:
            # 복리 단계 (재투자)
            capital = capital * (1 + pnl_pct / 100)
            compound_phase_trades += 1
        else:
            # 단리 단계 (고정 금액)
            if not switched:
                switched = True
                switch_at = i

            # threshold 금액으로 거래
            profit = threshold * (pnl_pct / 100)
            capital += profit
            simple_profit += profit
            simple_phase_trades += 1

    print(f"{name} 도달 시 전환:")
    print(f"  복리 단계: {compound_phase_trades:,}회")
    print(f"  단리 단계: {simple_phase_trades:,}회")
    print(f"  최종 자본: {capital:,.0f}원")
    print(f"  배율: {capital/initial_capital:,.1f}배")

    if switched:
        print(f"  전환 시점: {compound_phase_trades}번째 거래")
        print(f"  단리 수익: {simple_profit:,.0f}원\n")
    else:
        print(f"  전환 없음 (목표 미도달)\n")

print(f"{'='*80}")
print(f"권장 전략")
print(f"{'='*80}\n")

# 1천만원 전환 시나리오 상세
capital = initial_capital
threshold = 10_000_000
compound_trades = []
simple_trades = []

for trade in limit_trades:
    pnl_pct = trade['pnl'] * leverage

    if capital < threshold:
        capital_before = capital
        capital = capital * (1 + pnl_pct / 100)
        compound_trades.append({
            'pnl_pct': pnl_pct,
            'capital_before': capital_before,
            'capital_after': capital
        })
    else:
        profit = threshold * (pnl_pct / 100)
        simple_trades.append({
            'pnl_pct': pnl_pct,
            'profit': profit
        })
        capital += profit

print(f"추천: 1천만원 도달 시 단리 전환")
print(f"\n1단계 (복리): 100만원 → 1천만원")
print(f"  거래 횟수: {len(compound_trades):,}회")
print(f"  성장 배율: 10배")
print(f"  예상 기간: {len(compound_trades)/2056*5.8:.1f}년\n")

print(f"2단계 (단리): 1천만원 고정 운용")
print(f"  거래 횟수: {len(simple_trades):,}회")
print(f"  거래당 평균 수익: {sum(t['profit'] for t in simple_trades)/len(simple_trades):,.0f}원")
print(f"  총 수익: {sum(t['profit'] for t in simple_trades):,.0f}원")
print(f"  예상 기간: {len(simple_trades)/2056*5.8:.1f}년\n")

print(f"최종 결과:")
print(f"  총 자본: {capital:,.0f}원")
print(f"  순수익: {capital-initial_capital:,.0f}원")
print(f"  배율: {capital/initial_capital:,.1f}배")
print(f"  총 기간: {5.8:.1f}년\n")

print(f"{'='*80}")
print(f"시나리오 비교")
print(f"{'='*80}\n")

scenarios = [
    ("순수 복리", float('inf')),
    ("1천만원 전환", 10_000_000),
    ("5천만원 전환", 50_000_000),
    ("1억원 전환", 100_000_000),
    ("순수 단리", 0)
]

print(f"{'전략':<15} {'최종 자본':>15} {'배율':>10} {'리스크':>10}")
print(f"{'-'*80}")

for name, threshold in scenarios:
    capital = initial_capital

    for trade in limit_trades:
        pnl_pct = trade['pnl'] * leverage

        if threshold == 0:
            # 순수 단리
            profit = initial_capital * (pnl_pct / 100)
            capital += profit
        elif threshold == float('inf'):
            # 순수 복리 (오버플로우 방지)
            capital = capital * (1 + pnl_pct / 100)
            if capital > 1e15:  # 1000조 제한
                capital = 1e15
                break
        else:
            # 혼합 전략
            if capital < threshold:
                capital = capital * (1 + pnl_pct / 100)
            else:
                profit = threshold * (pnl_pct / 100)
                capital += profit

    # 리스크 판단
    if threshold == float('inf'):
        risk = "극고"
    elif threshold >= 100_000_000:
        risk = "중"
    elif threshold >= 10_000_000:
        risk = "저"
    else:
        risk = "극저"

    # 오버플로우 체크
    if capital > 1e15:
        print(f"{name:<15} {'오버플로우':>15} {'>1000000배':>10} {risk:>10}")
    else:
        print(f"{name:<15} {capital:>15,.0f} {capital/initial_capital:>10,.1f}배 {risk:>10}")

print(f"\n{'='*80}\n")

print(f"결론:")
print(f"  1. 초기 100만원 → 1천만원: 복리로 성장")
print(f"  2. 1천만원 도달 후: 단리로 전환 (안정적 수익)")
print(f"  3. 예상 최종 자본: {10_000_000 + sum(t['profit'] for t in simple_trades):,.0f}원")
print(f"  4. 리스크: 저 (복리는 1천만원까지만)\n")
