"""지정가 체결 디버깅"""
import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()

if dm.df_entry_full is None:
    raise ValueError("데이터가 비어 있습니다. load_historical() 실패")

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

# 샘플 100개 봉 분석
print("="*80)
print("샘플 100개 봉 분석 (0.001% 오프셋)")
print("="*80)

limit_offset = 0.00001
long_filled = 0
short_filled = 0

for i in range(100, 200):
    row = df_1h.iloc[i]
    open_price = row['open']
    low = row['low']
    high = row['high']

    # 롱 지정가
    long_limit = open_price * (1 - limit_offset)
    long_fill = low <= long_limit

    # 숏 지정가
    short_limit = open_price * (1 + limit_offset)
    short_fill = high >= short_limit

    if long_fill:
        long_filled += 1
    if short_fill:
        short_filled += 1

    if i < 110:  # 처음 10개만 출력
        print(f"\n[{i}] Open: {open_price:.2f}")
        print(f"  Long Limit: {long_limit:.2f} (Open - 0.001%)")
        print(f"  Low: {low:.2f} → {long_fill} (체결: {low} <= {long_limit:.2f})")
        print(f"  Short Limit: {short_limit:.2f} (Open + 0.001%)")
        print(f"  High: {high:.2f} → {short_fill} (체결: {high} >= {short_limit:.2f})")

print(f"\n{'='*80}")
print(f"체결률 (100개 봉 기준)")
print(f"{'='*80}")
print(f"롱 체결: {long_filled}/100 ({long_filled}%)")
print(f"숏 체결: {short_filled}/100 ({short_filled}%)")
print(f"{'='*80}\n")
