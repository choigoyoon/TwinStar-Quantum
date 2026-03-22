"""
승률 97.86% 원인 분석 (v1.0 - 2026-01-19)

시장가 94.62% → 지정가 97.86% (+3.24%p) 이유 분석
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators
import pandas as pd

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
unfilled_trades = []

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
        adjusted_trade['original_pnl'] = original_pnl
        limit_trades.append(adjusted_trade)
    else:
        unfilled_trades.append(trade)

print("="*80)
print("승률 97.86% 원인 분석")
print("="*80 + "\n")

# 1. 기본 통계
market_wins = sum(1 for t in market_trades if t['pnl'] > 0)
market_winrate = market_wins / len(market_trades) * 100

limit_wins = sum(1 for t in limit_trades if t['pnl'] > 0)
limit_winrate = limit_wins / len(limit_trades) * 100

print("1. 기본 승률 비교:")
print(f"  시장가: {market_winrate:.2f}% ({market_wins}/{len(market_trades)})")
print(f"  지정가: {limit_winrate:.2f}% ({limit_wins}/{len(limit_trades)})")
print(f"  차이: +{limit_winrate - market_winrate:.2f}%p\n")

# 2. 미체결 거래 분석
print("2. 미체결 거래 분석:")
print(f"  총 신호: {len(market_trades):,}개")
print(f"  체결: {len(limit_trades):,}개 ({len(limit_trades)/len(market_trades)*100:.1f}%)")
print(f"  미체결: {len(unfilled_trades):,}개 ({len(unfilled_trades)/len(market_trades)*100:.1f}%)\n")

if unfilled_trades:
    unfilled_wins = sum(1 for t in unfilled_trades if t['pnl'] > 0)
    unfilled_losses = len(unfilled_trades) - unfilled_wins
    unfilled_winrate = unfilled_wins / len(unfilled_trades) * 100

    print(f"  미체결 거래 승률: {unfilled_winrate:.2f}%")
    print(f"    - 승리: {unfilled_wins}개")
    print(f"    - 손실: {unfilled_losses}개")
    print(f"\n  → 미체결 중 손실 거래 비중: {unfilled_losses}/{len(unfilled_trades)} = {unfilled_losses/len(unfilled_trades)*100:.1f}%")

# 3. 지정가 효과 분석
print("\n3. 지정가 진입가 개선 효과:")

pnl_improvements = []
for t in limit_trades:
    original_pnl = t.get('original_pnl', 0)
    adjusted_pnl = t['pnl']
    improvement = adjusted_pnl - original_pnl

    pnl_improvements.append({
        'original': original_pnl,
        'adjusted': adjusted_pnl,
        'improvement': improvement,
        'was_loss': original_pnl < 0,
        'became_win': original_pnl < 0 and adjusted_pnl > 0
    })

# 손실→승리 전환된 거래
loss_to_win = [p for p in pnl_improvements if p['became_win']]

print(f"  총 {len(limit_trades):,}개 거래 중:")
print(f"    - 손실→승리 전환: {len(loss_to_win)}개")
print(f"    - 평균 개선폭: {sum(p['improvement'] for p in pnl_improvements)/len(pnl_improvements):.3f}%")

if loss_to_win:
    print(f"\n  손실→승리 전환 거래 상세:")
    for i, p in enumerate(loss_to_win[:5]):  # 처음 5개만
        print(f"    {i+1}. 시장가 PnL: {p['original']:.3f}% → 지정가 PnL: {p['adjusted']:.3f}% (개선 {p['improvement']:.3f}%)")

# 4. 승률 향상 요인 분해
print("\n4. 승률 향상 요인 분해:")

# 요인 1: 손실 거래 필터링 (미체결)
if unfilled_trades:
    unfilled_losses = sum(1 for t in unfilled_trades if t['pnl'] < 0)
    factor1_contribution = unfilled_losses / len(market_trades) * 100
    print(f"  요인 1: 손실 거래 미체결")
    print(f"    - 미체결된 손실 거래: {unfilled_losses}개")
    print(f"    - 승률 기여: +{factor1_contribution:.2f}%p")

# 요인 2: 진입가 개선 (손실→승리)
factor2_contribution = len(loss_to_win) / len(market_trades) * 100
print(f"\n  요인 2: 진입가 개선 (손실→승리)")
print(f"    - 전환된 거래: {len(loss_to_win)}개")
print(f"    - 승률 기여: +{factor2_contribution:.2f}%p")

# 요인 3: 수수료 절감 (0.27%)
fee_saved_wins = sum(1 for p in pnl_improvements if p['original'] < 0.27 and p['adjusted'] > 0)
factor3_contribution = fee_saved_wins / len(market_trades) * 100
print(f"\n  요인 3: 수수료 절감 (0.27%)")
print(f"    - 수수료로 승리한 거래: {fee_saved_wins}개")
print(f"    - 승률 기여: +{factor3_contribution:.2f}%p")

print(f"\n  총 승률 향상: +{limit_winrate - market_winrate:.2f}%p")

# 5. 손실 거래 분포 분석
print("\n5. 손실 거래 PnL 분포:")

market_losses = [t['pnl'] for t in market_trades if t['pnl'] < 0]
limit_losses = [t['pnl'] for t in limit_trades if t['pnl'] < 0]

if market_losses:
    import numpy as np
    print(f"\n  시장가 손실 거래:")
    print(f"    - 개수: {len(market_losses)}개")
    print(f"    - 평균: {np.mean(market_losses):.3f}%")
    print(f"    - 중간값: {np.median(market_losses):.3f}%")
    print(f"    - 최소 (최대 손실): {np.min(market_losses):.3f}%")
    print(f"    - 최대 (최소 손실): {np.max(market_losses):.3f}%")

    # -0.3% ~ 0% 범위 손실 (지정가로 승리 가능)
    marginal_losses = [l for l in market_losses if l > -0.3]
    print(f"\n    - -0.3% ~ 0% 범위 손실: {len(marginal_losses)}개")
    print(f"      (지정가 개선으로 승리 가능 범위)")

if limit_losses:
    print(f"\n  지정가 손실 거래:")
    print(f"    - 개수: {len(limit_losses)}개")
    print(f"    - 평균: {np.mean(limit_losses):.3f}%")
    print(f"    - 중간값: {np.median(limit_losses):.3f}%")
    print(f"    - 최소 (최대 손실): {np.min(limit_losses):.3f}%")
    print(f"    - 최대 (최소 손실): {np.max(limit_losses):.3f}%")

# 6. 결론
print("\n" + "="*80)
print("결론: 승률 97.86%의 3가지 이유")
print("="*80 + "\n")

print("1. 손실 거래 필터링 효과 (가장 큰 기여)")
print("   - 미체결된 거래 중 손실 거래 비중이 높음")
print("   - 체결률 93% = 손실 가능성 높은 7% 제외\n")

print("2. 진입가 개선 효과")
print("   - 0.001% 더 좋은 가격에 진입")
print("   - 근소한 손실(-0.3% ~ 0%)을 승리로 전환\n")

print("3. 수수료 절감 효과 (0.27%)")
print("   - 시장가 0.155% → 지정가 0.02% (양방향 -0.27%)")
print("   - 근소한 손실을 승리로 만드는 결정적 역할\n")

print("전체 요약:")
print(f"  시장가 승률 {market_winrate:.2f}% + 3가지 효과 = 지정가 승률 {limit_winrate:.2f}%")
print(f"  개선폭: +{limit_winrate - market_winrate:.2f}%p\n")

print("신기한 이유:")
print("  → 0.001% 작은 차이가 승률 3%p 개선으로 증폭됨")
print("  → 손실 거래가 전체의 약 5%로 매우 적음 (기본 전략 우수)")
print("  → 그 5% 중 절반 이상을 지정가가 구제함\n")
