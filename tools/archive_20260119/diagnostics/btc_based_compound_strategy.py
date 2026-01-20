"""
BTC 기반 복리 성장 전략 (v1.0 - 2026-01-19)

BTC 1~10개 매매 가능 수준까지 복리 성장 후 단리 전환
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
print(f"BTC 기반 복리 성장 전략 (5배 레버리지)")
print(f"{'='*80}\n")

# BTC 가격 설정 (현재 시장가 기준)
btc_price = 100_000_000  # 1억원 (약 $100,000)

# BTC 개수별 목표 자본
btc_targets = [
    (1, "BTC 1개"),
    (3, "BTC 3개"),
    (5, "BTC 5개"),
    (10, "BTC 10개"),
    (30, "BTC 30개"),
    (50, "BTC 50개"),
    (100, "BTC 100개"),
]

leverage = 5
initial_capital = 1_000_000  # 100만원

print(f"설정:")
print(f"  초기 자본: {initial_capital:,}원")
print(f"  레버리지: {leverage}x")
print(f"  BTC 가격: {btc_price:,}원 (1억원)")
print(f"  총 거래: {len(limit_trades):,}개\n")

print(f"{'='*80}")
print(f"BTC 개수별 복리 → 단리 전환 시나리오")
print(f"{'='*80}\n")

results = []

for btc_count, name in btc_targets:
    threshold = btc_price * btc_count
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

    results.append({
        'btc_count': btc_count,
        'name': name,
        'threshold': threshold,
        'compound_trades': compound_phase_trades,
        'simple_trades': simple_phase_trades,
        'final_capital': capital,
        'simple_profit': simple_profit,
        'switched': switched
    })

    print(f"{name} ({threshold/100_000_000:,.0f}억원) 도달 시 전환:")
    print(f"  복리 단계: {compound_phase_trades:,}회")
    print(f"  단리 단계: {simple_phase_trades:,}회")
    print(f"  최종 자본: {capital:,.0f}원 ({capital/100_000_000:,.1f}억원)")
    print(f"  배율: {capital/initial_capital:,.1f}배")

    if switched:
        print(f"  전환 시점: {compound_phase_trades}번째 거래")
        print(f"  복리 기간: {compound_phase_trades/2056*5.8:.2f}년")
        print(f"  단리 기간: {simple_phase_trades/2056*5.8:.2f}년")
        print(f"  단리 수익: {simple_profit:,.0f}원 ({simple_profit/100_000_000:,.1f}억원)\n")
    else:
        print(f"  전환 없음 (목표 미도달)\n")

print(f"{'='*80}")
print(f"권장 전략 분석")
print(f"{'='*80}\n")

# BTC 10개 전환 시나리오 상세
r10 = results[3]  # BTC 10개

print(f"추천: BTC 10개 ({r10['threshold']/100_000_000:,.0f}억원) 도달 시 단리 전환\n")

print(f"1단계 (복리): 100만원 → {r10['threshold']/100_000_000:,.0f}억원 (BTC 10개 매매 가능)")
print(f"  거래 횟수: {r10['compound_trades']:,}회")
print(f"  성장 배율: {r10['threshold']/initial_capital:,.0f}배")
print(f"  예상 기간: {r10['compound_trades']/2056*5.8:.2f}년\n")

print(f"2단계 (단리): {r10['threshold']/100_000_000:,.0f}억원 고정 운용")
print(f"  거래 횟수: {r10['simple_trades']:,}회")
print(f"  거래당 평균 수익: {r10['simple_profit']/r10['simple_trades']:,.0f}원")
print(f"  거래당 평균 수익: {r10['simple_profit']/r10['simple_trades']/btc_price:.3f} BTC")
print(f"  총 수익: {r10['simple_profit']:,.0f}원 ({r10['simple_profit']/100_000_000:,.1f}억원)")
print(f"  예상 기간: {r10['simple_trades']/2056*5.8:.2f}년\n")

print(f"최종 결과:")
print(f"  총 자본: {r10['final_capital']:,.0f}원 ({r10['final_capital']/100_000_000:,.1f}억원)")
print(f"  순수익: {r10['final_capital']-initial_capital:,.0f}원")
print(f"  배율: {r10['final_capital']/initial_capital:,.1f}배")
print(f"  총 기간: 5.8년\n")

print(f"{'='*80}")
print(f"시나리오 비교 (100만원 시작)")
print(f"{'='*80}\n")

print(f"{'전환 기준':<12} {'복리 기간':>10} {'최종 자본':>15} {'배율':>10} {'리스크':>10}")
print(f"{'-'*80}")

for r in results[:7]:
    # 리스크 판단
    if r['btc_count'] >= 100:
        risk = "극고"
    elif r['btc_count'] >= 30:
        risk = "고"
    elif r['btc_count'] >= 10:
        risk = "중"
    elif r['btc_count'] >= 5:
        risk = "저"
    else:
        risk = "극저"

    compound_years = r['compound_trades']/2056*5.8

    print(f"{r['name']:<12} {compound_years:>9.2f}년 {r['final_capital']:>15,.0f} {r['final_capital']/initial_capital:>10,.1f}배 {risk:>10}")

print(f"\n{'='*80}")
print(f"BTC 개수별 매매 특성")
print(f"{'='*80}\n")

print(f"BTC 1개 매매 ({btc_price:,}원):")
print(f"  - 레버리지 5배 시 필요 증거금: {btc_price/5:,}원")
print(f"  - 특성: 소액 매매, 슬리피지 최소\n")

print(f"BTC 10개 매매 ({btc_price*10:,}원):")
print(f"  - 레버리지 5배 시 필요 증거금: {btc_price*10/5:,}원")
print(f"  - 특성: 중형 매매, 균형잡힌 운용\n")

print(f"BTC 100개 매매 ({btc_price*100:,}원):")
print(f"  - 레버리지 5배 시 필요 증거금: {btc_price*100/5:,}원")
print(f"  - 특성: 대형 매매, 슬리피지 주의 필요\n")

print(f"{'='*80}")
print(f"최종 권장")
print(f"{'='*80}\n")

print(f"목표: BTC 10개 매매 가능 수준 (10억원)")
print(f"\n이유:")
print(f"  1. 복리 성장: 100만원 → 10억원 (1000배)")
print(f"  2. 복리 기간: {r10['compound_trades']/2056*5.8:.2f}년 (합리적)")
print(f"  3. 매매 규모: BTC 10개 = 중형 매매 (최적)")
print(f"  4. 슬리피지: 여전히 낮은 수준")
print(f"  5. 단리 수익: 연 {r10['simple_profit']/(r10['simple_trades']/2056*5.8)/100_000_000:,.1f}억원")
print(f"\n전략:")
print(f"  Phase 1: 100만원 → 10억원 (복리, {r10['compound_trades']}회)")
print(f"  Phase 2: 10억원 고정 매매 (단리, {r10['simple_trades']}회)")
print(f"  최종: {r10['final_capital']/100_000_000:,.1f}억원 ({r10['final_capital']/initial_capital:,.1f}배)\n")
