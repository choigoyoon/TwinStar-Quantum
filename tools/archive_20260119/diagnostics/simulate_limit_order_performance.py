"""
지정가 주문 성능 시뮬레이션 (v1.0 - 2026-01-19)

실제 체결된 거래의 승률/Sharpe/MDD를 계산하여 시장가 대비 성능 비교
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
print(f"1단계: 시장가 백테스트 (기준선)")
print(f"{'='*80}\n")

# 시장가 백테스트
market_trades = strategy.run_backtest(
    df_pattern=df_1h,
    df_entry=df_1h,
    slippage=0.001,
    **CORRECT_PARAMS
)

print(f"총 거래: {len(market_trades):,}개\n")

# 시장가 메트릭
market_metrics = calculate_backtest_metrics(market_trades, leverage=1, capital=100.0)

print(f"{'='*80}")
print(f"시장가 백테스트 결과")
print(f"{'='*80}")
print(f"총 거래:       {market_metrics['total_trades']:,}회")
print(f"승률:          {market_metrics['win_rate']:.2f}%")
print(f"거래당 PnL:    {market_metrics['avg_pnl']:.3f}%")
print(f"총 PnL:        {market_metrics['total_pnl']:.2f}%")
print(f"MDD:           {market_metrics['mdd']:.2f}%")
print(f"Sharpe Ratio:  {market_metrics['sharpe_ratio']:.2f}")
print(f"Profit Factor: {market_metrics['profit_factor']:.2f}")
print(f"{'='*80}\n")

print(f"{'='*80}")
print(f"2단계: 지정가 체결 시뮬레이션 (0.001% 오프셋)")
print(f"{'='*80}\n")

# 지정가 거래 시뮬레이션
limit_offset = 0.00001  # 0.001%
limit_trades = []
unfilled_count = 0

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
        # 체결됨: 진입가만 조정, 나머지는 동일
        adjusted_trade = trade.copy()

        # 원래 진입가와 새 진입가 차이 계산
        original_entry = trade.get('entry_price', open_price)
        entry_diff_pct = (actual_entry - original_entry) / original_entry

        # PnL 조정 (진입가 차이만큼 개선)
        original_pnl = trade.get('pnl', 0)

        if side == 'Long':
            # 롱: 더 낮은 가격에 샀으므로 PnL 개선
            adjusted_pnl = original_pnl - (entry_diff_pct * 100)
        else:
            # 숏: 더 높은 가격에 팔았으므로 PnL 개선
            adjusted_pnl = original_pnl + (entry_diff_pct * 100)

        # 수수료 차이 반영
        # 시장가: 0.055% Taker, 0.1% 슬리피지 = 0.155% 총 비용
        # 지정가: 0.02% Maker, 0% 슬리피지 = 0.02% 총 비용
        # 차이: -0.135% (양방향이므로 -0.27%)
        fee_improvement = 0.27
        adjusted_pnl += fee_improvement

        adjusted_trade['pnl'] = adjusted_pnl
        adjusted_trade['entry_price'] = actual_entry
        limit_trades.append(adjusted_trade)
    else:
        unfilled_count += 1

fill_rate = len(limit_trades) / len(market_trades) * 100
print(f"체결된 거래: {len(limit_trades):,}개 / {len(market_trades):,}개 ({fill_rate:.1f}%)")
print(f"미체결: {unfilled_count:,}개 ({100-fill_rate:.1f}%)\n")

# 지정가 메트릭
limit_metrics = calculate_backtest_metrics(limit_trades, leverage=1, capital=100.0)

print(f"{'='*80}")
print(f"지정가 백테스트 결과")
print(f"{'='*80}")
print(f"총 거래:       {limit_metrics['total_trades']:,}회")
print(f"승률:          {limit_metrics['win_rate']:.2f}%")
print(f"거래당 PnL:    {limit_metrics['avg_pnl']:.3f}%")
print(f"총 PnL:        {limit_metrics['total_pnl']:.2f}%")
print(f"MDD:           {limit_metrics['mdd']:.2f}%")
print(f"Sharpe Ratio:  {limit_metrics['sharpe_ratio']:.2f}")
print(f"Profit Factor: {limit_metrics['profit_factor']:.2f}")
print(f"{'='*80}\n")

print(f"{'='*80}")
print(f"시장가 vs 지정가 비교")
print(f"{'='*80}")
print(f"{'지표':<15} {'시장가':>12} {'지정가':>12} {'차이':>12}")
print(f"{'-'*80}")

# 거래수
trade_diff = limit_metrics['total_trades'] - market_metrics['total_trades']
trade_diff_pct = trade_diff / market_metrics['total_trades'] * 100
print(f"{'거래 횟수':<15} {market_metrics['total_trades']:>12,} {limit_metrics['total_trades']:>12,} {trade_diff:>11,} ({trade_diff_pct:+.1f}%)")

# 승률
wr_diff = limit_metrics['win_rate'] - market_metrics['win_rate']
print(f"{'승률':<15} {market_metrics['win_rate']:>11.2f}% {limit_metrics['win_rate']:>11.2f}% {wr_diff:>11.2f}%p")

# 거래당 PnL
pnl_diff = limit_metrics['avg_pnl'] - market_metrics['avg_pnl']
pnl_diff_pct = pnl_diff / market_metrics['avg_pnl'] * 100
print(f"{'거래당 PnL':<15} {market_metrics['avg_pnl']:>11.3f}% {limit_metrics['avg_pnl']:>11.3f}% {pnl_diff:>11.3f}% ({pnl_diff_pct:+.1f}%)")

# 총 PnL
total_pnl_diff = limit_metrics['total_pnl'] - market_metrics['total_pnl']
total_pnl_diff_pct = total_pnl_diff / market_metrics['total_pnl'] * 100
print(f"{'총 PnL':<15} {market_metrics['total_pnl']:>11.2f}% {limit_metrics['total_pnl']:>11.2f}% {total_pnl_diff:>11.2f}% ({total_pnl_diff_pct:+.1f}%)")

# MDD
mdd_diff = limit_metrics['mdd'] - market_metrics['mdd']
mdd_diff_pct = mdd_diff / market_metrics['mdd'] * 100 if market_metrics['mdd'] > 0 else 0
print(f"{'MDD':<15} {market_metrics['mdd']:>11.2f}% {limit_metrics['mdd']:>11.2f}% {mdd_diff:>11.2f}% ({mdd_diff_pct:+.1f}%)")

# Sharpe
sharpe_diff = limit_metrics['sharpe_ratio'] - market_metrics['sharpe_ratio']
sharpe_diff_pct = sharpe_diff / market_metrics['sharpe_ratio'] * 100 if market_metrics['sharpe_ratio'] > 0 else 0
print(f"{'Sharpe':<15} {market_metrics['sharpe_ratio']:>12.2f} {limit_metrics['sharpe_ratio']:>12.2f} {sharpe_diff:>12.2f} ({sharpe_diff_pct:+.1f}%)")

# Profit Factor
pf_diff = limit_metrics['profit_factor'] - market_metrics['profit_factor']
pf_diff_pct = pf_diff / market_metrics['profit_factor'] * 100 if market_metrics['profit_factor'] > 0 else 0
print(f"{'Profit Factor':<15} {market_metrics['profit_factor']:>12.2f} {limit_metrics['profit_factor']:>12.2f} {pf_diff:>12.2f} ({pf_diff_pct:+.1f}%)")

print(f"{'='*80}\n")

print(f"{'='*80}")
print(f"결론")
print(f"{'='*80}\n")

# 체결률
if fill_rate >= 90:
    print(f"1. 체결률: {fill_rate:.1f}% (충분히 높음)")
else:
    print(f"1. 체결률: {fill_rate:.1f}% (낮음, 다중 심볼 권장)")

# 승률
if wr_diff > 0:
    print(f"2. 승률: +{wr_diff:.2f}%p 개선 (진입 품질 향상)")
elif wr_diff < -1:
    print(f"2. 승률: {wr_diff:.2f}%p 하락 (주의 필요)")
else:
    print(f"2. 승률: {wr_diff:.2f}%p (거의 동일)")

# 거래당 PnL
if pnl_diff > 0:
    print(f"3. 거래당 PnL: +{pnl_diff:.3f}% 개선 ({pnl_diff_pct:+.1f}%, 비용 절감 효과)")
elif pnl_diff < -0.1:
    print(f"3. 거래당 PnL: {pnl_diff:.3f}% 하락 ({pnl_diff_pct:+.1f}%)")
else:
    print(f"3. 거래당 PnL: {pnl_diff:.3f}% (거의 동일)")

# 총 PnL
if total_pnl_diff > 0:
    print(f"4. 총 PnL: +{total_pnl_diff:.2f}% 개선 ({total_pnl_diff_pct:+.1f}%)")
else:
    print(f"4. 총 PnL: {total_pnl_diff:.2f}% ({total_pnl_diff_pct:+.1f}%, 거래 감소 영향)")

# Sharpe
if sharpe_diff > 0:
    print(f"5. Sharpe Ratio: +{sharpe_diff:.2f} 개선 ({sharpe_diff_pct:+.1f}%, 리스크 대비 수익 향상)")
elif sharpe_diff < -1:
    print(f"5. Sharpe Ratio: {sharpe_diff:.2f} 하락 ({sharpe_diff_pct:+.1f}%)")
else:
    print(f"5. Sharpe Ratio: {sharpe_diff:.2f} (거의 동일)")

# 최종 권장
print(f"\n최종 권장:")
if fill_rate >= 90 and pnl_diff > 0.1 and wr_diff >= -1:
    print(f"  지정가 주문 사용 권장")
    print(f"  - 체결률 {fill_rate:.1f}% (충분)")
    print(f"  - 거래당 PnL +{pnl_diff:.3f}% 개선")
    print(f"  - 수수료 절감: 0.055% -> 0.02% (-64%)")
    print(f"  - 슬리피지 제거: 0.1% -> 0% (-100%)")
elif fill_rate < 50:
    print(f"  시장가 주문 유지 권장")
    print(f"  - 체결률 {fill_rate:.1f}% (너무 낮음)")
    print(f"  - 또는 다중 심볼 운영 (BTC + ETH + SOL 등)")
else:
    print(f"  상황에 따라 선택")
    print(f"  - 체결률: {fill_rate:.1f}%")
    print(f"  - 거래당 PnL 개선: {pnl_diff:+.3f}%")
    print(f"  - 다중 심볼 운영 시 지정가 유리")

print(f"\n{'='*80}\n")
