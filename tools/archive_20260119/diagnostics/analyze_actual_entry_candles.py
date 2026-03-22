"""
실제 시장가 진입 봉의 Low-Open 분포 분석

시장가 백테스트에서 진입한 2,211개 봉의 실제 Low drop을 분석
이게 진짜 체결률입니다!
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
print("시장가 백테스트 실행 중...\n")

trades = strategy.run_backtest(
    df_pattern=df_1h,
    df_entry=df_1h,
    slippage=0.001,
    **CORRECT_PARAMS
)

print(f"총 거래: {len(trades):,}개\n")

# 진입 봉의 Low-Open 분석
long_low_drops = []
short_high_rises = []

for trade in trades:
    entry_idx = trade.get('entry_idx', 0)
    side = trade.get('type', 'Long')

    if entry_idx >= len(df_1h):
        continue

    entry_candle = df_1h.iloc[entry_idx]
    open_price = entry_candle['open']
    low = entry_candle['low']
    high = entry_candle['high']

    if side == 'Long':
        low_drop = (low - open_price) / open_price * 100
        long_low_drops.append(low_drop)
    else:
        high_rise = (high - open_price) / open_price * 100
        short_high_rises.append(high_rise)

print(f"{'='*80}")
print(f"실제 진입 봉 분석")
print(f"{'='*80}")
print(f"롱 진입: {len(long_low_drops):,}개")
print(f"숏 진입: {len(short_high_rises):,}개\n")

# 0.001% 오프셋 체결률 계산
limit_offset = 0.001  # 0.001%

# 롱 체결률
long_filled = sum(1 for drop in long_low_drops if drop <= -limit_offset)
long_fill_rate = long_filled / len(long_low_drops) * 100 if long_low_drops else 0

# 숏 체결률
short_filled = sum(1 for rise in short_high_rises if rise >= limit_offset)
short_fill_rate = short_filled / len(short_high_rises) * 100 if short_high_rises else 0

print(f"{'='*80}")
print(f"0.001% 오프셋 체결률 (실제 진입 봉 기준)")
print(f"{'='*80}")
print(f"\n롱 진입 ({len(long_low_drops):,}개):")
print(f"  Low <= Open - 0.001%: {long_filled:,}개 ({long_fill_rate:.1f}%)")
print(f"  미체결: {len(long_low_drops) - long_filled:,}개 ({100 - long_fill_rate:.1f}%)")

print(f"\n숏 진입 ({len(short_high_rises):,}개):")
print(f"  High >= Open + 0.001%: {short_filled:,}개 ({short_fill_rate:.1f}%)")
print(f"  미체결: {len(short_high_rises) - short_filled:,}개 ({100 - short_fill_rate:.1f}%)")

total_filled = long_filled + short_filled
total_trades = len(long_low_drops) + len(short_high_rises)
total_fill_rate = total_filled / total_trades * 100 if total_trades > 0 else 0

print(f"\n전체 체결률: {total_filled:,}/{total_trades:,} ({total_fill_rate:.1f}%)")
print(f"{'='*80}\n")

# Low drop 분포 히스토그램
print(f"{'='*80}")
print(f"롱 Low Drop 분포 (실제 진입 봉)")
print(f"{'='*80}\n")

bins = [
    (-10, -0.5), (-0.5, -0.1), (-0.1, -0.05), (-0.05, -0.02),
    (-0.02, -0.01), (-0.01, -0.005), (-0.005, -0.002), (-0.002, -0.001),
    (-0.001, 0), (0, 0.001), (0.001, 10)
]

for low_bound, high_bound in bins:
    count = sum(1 for drop in long_low_drops if low_bound <= drop < high_bound)
    pct = count / len(long_low_drops) * 100 if long_low_drops else 0
    bar = '#' * int(pct)

    if low_bound == 0:
        label = "0% (O=L)"
    elif low_bound == -0.001:
        label = "-0.001~0%"
    else:
        label = f"{low_bound:.3f}~{high_bound:.3f}%"

    print(f"{label:>17}: {bar} {count:,}개 ({pct:.1f}%)")

print(f"\n{'='*80}")
print(f"결론")
print(f"{'='*80}")
print(f"\n실제 시장가 진입 봉 기준 체결률: {total_fill_rate:.1f}%")
print(f"entry_ohl_analysis.csv 예상: 11.1%")
print(f"차이: {total_fill_rate - 11.1:.1f}%p\n")

if total_fill_rate > 50:
    print("→ 체결률이 50% 이상입니다!")
    print("→ 0.001% 오프셋은 실제로 높은 체결률을 보입니다.")
    print("→ 시장가 진입 봉은 일반 봉과 다른 특성을 가집니다.")
else:
    print("→ 체결률이 50% 미만입니다.")
    print("→ 0.001% 오프셋으로는 절반 이상의 기회를 놓칩니다.")

print(f"{'='*80}\n")
