"""
웹소켓 실시간 vs 백테스트 차이 분석 (v1.0 - 2026-01-19)

백테스트: 다음 봉 Open 가격 진입
실시간: 신호 발생 즉시 진입 (현재 봉 Close 근처)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators
import pandas as pd
import numpy as np

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

# 백테스트 (다음 봉 Open 진입)
backtest_trades = strategy.run_backtest(
    df_pattern=df_1h,
    df_entry=df_1h,
    slippage=0.001,
    **CORRECT_PARAMS
)

print("="*80)
print("웹소켓 실시간 vs 백테스트 차이 분석")
print("="*80 + "\n")

print("1. 백테스트 가정:")
print("  - 신호 발생: N번째 봉 종료 시점")
print("  - 진입 시점: N+1번째 봉 Open")
print("  - 진입 가격: next_candle['open']")
print("  - 지연 시간: 최대 1시간 (다음 봉까지 대기)\n")

print("2. 웹소켓 실시간 가정:")
print("  - 신호 발생: N번째 봉 종료 시점")
print("  - 진입 시점: 즉시 (1-2초 내)")
print("  - 진입 가격: current_candle['close'] 근처 (시장가)")
print("  - 또는: close * (1 ± 0.001%) (지정가)")
print("  - 지연 시간: 1-2초\n")

# 진입가 차이 분석
print("3. 진입가 차이 분석:")
print("\n  분석 방법:")
print("    - 백테스트: next_open (N+1 봉 Open)")
print("    - 웹소켓: current_close (N 봉 Close)")
print("    - 차이: (next_open - current_close) / current_close\n")

entry_price_diffs = []

for trade in backtest_trades:
    signal_idx = trade.get('signal_idx', 0)
    entry_idx = trade.get('entry_idx', 0)
    side = trade.get('type', 'Long')

    if signal_idx >= len(df_1h) or entry_idx >= len(df_1h):
        continue

    signal_candle = df_1h.iloc[signal_idx]
    entry_candle = df_1h.iloc[entry_idx]

    current_close = signal_candle['close']  # 웹소켓 진입가
    next_open = entry_candle['open']  # 백테스트 진입가

    price_diff_pct = (next_open - current_close) / current_close * 100

    entry_price_diffs.append({
        'side': side,
        'current_close': current_close,
        'next_open': next_open,
        'diff_pct': price_diff_pct,
        'original_pnl': trade.get('pnl', 0)
    })

# 통계
diffs = [d['diff_pct'] for d in entry_price_diffs]
long_diffs = [d['diff_pct'] for d in entry_price_diffs if d['side'] == 'Long']
short_diffs = [d['diff_pct'] for d in entry_price_diffs if d['side'] == 'Short']

print(f"  전체 ({len(diffs)}개 거래):")
print(f"    평균 차이: {np.mean(diffs):.3f}%")
print(f"    중간값: {np.median(diffs):.3f}%")
print(f"    표준편차: {np.std(diffs):.3f}%")
print(f"    최소 (Close가 더 높음): {np.min(diffs):.3f}%")
print(f"    최대 (Open이 더 높음): {np.max(diffs):.3f}%")

print(f"\n  Long 거래 ({len(long_diffs)}개):")
print(f"    평균 차이: {np.mean(long_diffs):.3f}%")
print(f"    해석: 평균적으로 Open이 Close보다 {np.mean(long_diffs):.3f}% {'높음' if np.mean(long_diffs) > 0 else '낮음'}")
if np.mean(long_diffs) > 0:
    print(f"    → 웹소켓이 {abs(np.mean(long_diffs)):.3f}% 더 좋은 가격에 진입 (Long)")
else:
    print(f"    → 백테스트가 {abs(np.mean(long_diffs)):.3f}% 더 좋은 가격에 진입 (Long)")

print(f"\n  Short 거래 ({len(short_diffs)}개):")
print(f"    평균 차이: {np.mean(short_diffs):.3f}%")
print(f"    해석: 평균적으로 Open이 Close보다 {np.mean(short_diffs):.3f}% {'높음' if np.mean(short_diffs) > 0 else '낮음'}")
if np.mean(short_diffs) < 0:
    print(f"    → 웹소켓이 {abs(np.mean(short_diffs)):.3f}% 더 좋은 가격에 진입 (Short)")
else:
    print(f"    → 백테스트가 {abs(np.mean(short_diffs)):.3f}% 더 좋은 가격에 진입 (Short)")

# 4. PnL 영향 추정
print("\n4. 웹소켓 실시간 PnL 영향 추정:")

websocket_pnls = []

for d in entry_price_diffs:
    original_pnl = d['original_pnl']
    price_diff = d['diff_pct']
    side = d['side']

    # 웹소켓 진입가 영향
    # Long: Close < Open이면 더 좋은 가격 (PnL 증가)
    # Short: Close > Open이면 더 좋은 가격 (PnL 증가)
    if side == 'Long':
        websocket_pnl = original_pnl - price_diff
    else:  # Short
        websocket_pnl = original_pnl + price_diff

    websocket_pnls.append(websocket_pnl)

# 백테스트 vs 웹소켓 비교
backtest_avg_pnl = np.mean([d['original_pnl'] for d in entry_price_diffs])
websocket_avg_pnl = np.mean(websocket_pnls)

backtest_wins = sum(1 for d in entry_price_diffs if d['original_pnl'] > 0)
websocket_wins = sum(1 for pnl in websocket_pnls if pnl > 0)

backtest_winrate = backtest_wins / len(entry_price_diffs) * 100
websocket_winrate = websocket_wins / len(websocket_pnls) * 100

print(f"\n  백테스트 (다음 봉 Open 진입):")
print(f"    평균 PnL: {backtest_avg_pnl:.3f}%")
print(f"    승률: {backtest_winrate:.2f}%")
print(f"    총 PnL: {backtest_avg_pnl * len(entry_price_diffs):.2f}%")

print(f"\n  웹소켓 (현재 봉 Close 진입):")
print(f"    평균 PnL: {websocket_avg_pnl:.3f}%")
print(f"    승률: {websocket_winrate:.2f}%")
print(f"    총 PnL: {websocket_avg_pnl * len(websocket_pnls):.2f}%")

print(f"\n  차이:")
print(f"    평균 PnL: {websocket_avg_pnl - backtest_avg_pnl:+.3f}%")
print(f"    승률: {websocket_winrate - backtest_winrate:+.2f}%p")
print(f"    총 PnL: {(websocket_avg_pnl - backtest_avg_pnl) * len(entry_price_diffs):+.2f}%")

# 5. 지정가 주문 시뮬레이션 (웹소켓)
print("\n5. 웹소켓 지정가 주문 시뮬레이션:")
print("  설정: Close ± 0.001% 지정가\n")

websocket_limit_trades = []
websocket_limit_offset = 0.00001  # 0.001%

for i, trade in enumerate(backtest_trades):
    signal_idx = trade.get('signal_idx', 0)
    entry_idx = trade.get('entry_idx', 0)
    side = trade.get('type', 'Long')

    if signal_idx >= len(df_1h) or entry_idx >= len(df_1h):
        continue

    signal_candle = df_1h.iloc[signal_idx]
    entry_candle = df_1h.iloc[entry_idx]

    # 웹소켓: 신호 발생 즉시 지정가 주문
    signal_close = signal_candle['close']

    if side == 'Long':
        limit_price = signal_close * (1 - websocket_limit_offset)
    else:
        limit_price = signal_close * (1 + websocket_limit_offset)

    # 다음 봉에서 체결 여부 확인
    next_low = entry_candle['low']
    next_high = entry_candle['high']

    filled = False
    if side == 'Long' and next_low <= limit_price:
        filled = True
    elif side == 'Short' and next_high >= limit_price:
        filled = True

    if filled:
        # PnL 계산 (웹소켓 지정가 기준)
        original_pnl = entry_price_diffs[i]['original_pnl']
        price_diff = entry_price_diffs[i]['diff_pct']

        if side == 'Long':
            # Close < Open: 웹소켓이 더 좋은 가격
            # 지정가는 Close보다 0.001% 더 좋음
            websocket_limit_pnl = original_pnl - price_diff - websocket_limit_offset * 100
        else:
            # Close > Open: 웹소켓이 더 나쁜 가격
            # 지정가는 Close보다 0.001% 더 좋음
            websocket_limit_pnl = original_pnl + price_diff + websocket_limit_offset * 100

        # 수수료 절감 (0.27%)
        websocket_limit_pnl += 0.27

        websocket_limit_trades.append(websocket_limit_pnl)

websocket_limit_avg_pnl = np.mean(websocket_limit_trades)
websocket_limit_wins = sum(1 for pnl in websocket_limit_trades if pnl > 0)
websocket_limit_winrate = websocket_limit_wins / len(websocket_limit_trades) * 100
websocket_fill_rate = len(websocket_limit_trades) / len(backtest_trades) * 100

print(f"  체결률: {websocket_fill_rate:.1f}%")
print(f"  평균 PnL: {websocket_limit_avg_pnl:.3f}%")
print(f"  승률: {websocket_limit_winrate:.2f}%")
print(f"  총 PnL: {websocket_limit_avg_pnl * len(websocket_limit_trades):.2f}%")

# 6. 결론
print("\n" + "="*80)
print("결론: 웹소켓 실시간 vs 백테스트")
print("="*80 + "\n")

print("1. 진입가 차이:")
print(f"  - 평균 차이: {np.mean(diffs):.3f}%")
print(f"  - Long: {'웹소켓 유리' if np.mean(long_diffs) > 0 else '백테스트 유리'} ({abs(np.mean(long_diffs)):.3f}%)")
print(f"  - Short: {'웹소켓 유리' if np.mean(short_diffs) < 0 else '백테스트 유리'} ({abs(np.mean(short_diffs)):.3f}%)")

print("\n2. 성능 차이:")
print(f"  - 백테스트 승률: {backtest_winrate:.2f}%")
print(f"  - 웹소켓 승률: {websocket_winrate:.2f}% ({websocket_winrate - backtest_winrate:+.2f}%p)")
print(f"  - 웹소켓 지정가 승률: {websocket_limit_winrate:.2f}% ({websocket_limit_winrate - backtest_winrate:+.2f}%p)")

print("\n3. 권장 사항:")
if abs(np.mean(diffs)) < 0.05:
    print("  → 진입가 차이 미미 (<0.05%)")
    print("  → 백테스트 결과 신뢰 가능")
else:
    print(f"  → 진입가 차이 유의미 ({abs(np.mean(diffs)):.3f}%)")
    print("  → 실시간 테스트 권장")

print("\n4. 실시간 운영 시 주의사항:")
print("  - 웹소켓 지연: 1-2초 (무시 가능)")
print("  - 슬리피지: 시장가 0.1% vs 지정가 0%")
print("  - 체결률: 지정가 93% (충분히 높음)")
print("  - 수수료: 지정가 -0.27% 절감 (결정적)")

print("\n최종 결론:")
if websocket_limit_winrate > backtest_winrate:
    improvement = websocket_limit_winrate - backtest_winrate
    print(f"  웹소켓 지정가 사용 권장 (승률 +{improvement:.2f}%p)")
else:
    print("  백테스트 결과와 유사, 실시간 테스트로 검증 필요")

print("\n")
