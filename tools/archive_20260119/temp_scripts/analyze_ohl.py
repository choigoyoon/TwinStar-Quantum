"""진입 시점 Open/High/Low 분석 (v7.25)

Long: Open 대비 Low가 얼마나 떨어지는지 (더 싸게 살 기회)
Short: Open 대비 High가 얼마나 오르는지 (더 비싸게 팔 기회)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core

# 최적 파라미터 (Fine-Tuning 결과)
OPTIMAL_PARAMS = {
    'atr_mult': 1.25,
    'filter_tf': '4h',
    'trail_start_r': 0.4,
    'trail_dist_r': 0.05,
    'entry_tf': '1h',
    'entry_validity_hours': 6.0,
    'leverage': 1,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7
}

print("="*80)
print("진입 시점 Open/High/Low 분석")
print("="*80)

# 1. 데이터 로드
print("\n데이터 로딩...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()

if dm.df_entry_full is None:
    print("❌ 데이터 로드 실패")
    sys.exit(1)

df = dm.df_entry_full.copy()
print(f"데이터 로드 완료: {len(df):,}개 캔들")

# 2. 백테스트 실행
print("\n백테스트 실행 중...")
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

result = strategy.run_backtest(
    df_pattern=df,
    df_entry=df,
    **OPTIMAL_PARAMS
)

trades = result if isinstance(result, list) else result[0]
print(f"백테스트 완료: {len(trades)}개 거래")

# 3. 진입 봉 분석
print("\n진입 봉 OHLC 분석 중...")

entry_data = []

for i, trade in enumerate(trades):
    side = trade.get('type', 'Long')  # 'type' 필드 사용
    entry_idx = trade.get('entry_idx')

    if entry_idx is None or entry_idx >= len(df):
        continue

    # 진입 봉 직접 가져오기
    candle = df.iloc[entry_idx]

    o = candle['open']
    h = candle['high']
    l = candle['low']

    # Long: Low가 Open보다 낮으면 유리
    # Short: High가 Open보다 높으면 유리
    low_drop = (l - o) / o * 100  # 음수 = 떨어짐
    high_rise = (h - o) / o * 100  # 양수 = 올랐음

    entry_data.append({
        'side': side,
        'open': o,
        'high': h,
        'low': l,
        'low_drop': low_drop,
        'high_rise': high_rise,
    })

df_entry = pd.DataFrame(entry_data)
print(f"진입 봉 추출 완료: {len(df_entry)}개")

# 4. Long/Short 분리
df_long = df_entry[df_entry['side'] == 'Long']
df_short = df_entry[df_entry['side'] == 'Short']

print("\n" + "="*80)
print("분석 결과")
print("="*80)

# Long 분석
if len(df_long) > 0:
    print(f"\n[Long 진입 분석] ({len(df_long)}개)")
    print("-"*80)
    print("Open 대비 Low 하락 (더 싸게 살 기회):")
    print(f"  평균:     {df_long['low_drop'].mean():>8.3f}%")
    print(f"  중간값:   {df_long['low_drop'].median():>8.3f}%")
    print(f"  표준편차: {df_long['low_drop'].std():>8.3f}%")
    print(f"  최대하락: {df_long['low_drop'].min():>8.3f}% (가장 유리)")
    print(f"  25%:      {df_long['low_drop'].quantile(0.25):>8.3f}%")

    print("\nOpen 대비 High 상승 (놓친 기회):")
    print(f"  평균:     {df_long['high_rise'].mean():>8.3f}%")
    print(f"  최대:     {df_long['high_rise'].max():>8.3f}%")

    # 지정가 권장
    long_limit = df_long['low_drop'].mean() * 0.5
    print(f"\n✅ 지정가 권장: Open {long_limit:+.3f}% (Low 평균의 50%)")
    print(f"   → 약 50% 확률로 체결 예상")

# Short 분석
if len(df_short) > 0:
    print(f"\n[Short 진입 분석] ({len(df_short)}개)")
    print("-"*80)
    print("Open 대비 High 상승 (더 비싸게 팔 기회):")
    print(f"  평균:     {df_short['high_rise'].mean():>8.3f}%")
    print(f"  중간값:   {df_short['high_rise'].median():>8.3f}%")
    print(f"  표준편차: {df_short['high_rise'].std():>8.3f}%")
    print(f"  최대상승: {df_short['high_rise'].max():>8.3f}% (가장 유리)")
    print(f"  75%:      {df_short['high_rise'].quantile(0.75):>8.3f}%")

    print("\nOpen 대비 Low 하락 (놓친 기회):")
    print(f"  평균:     {df_short['low_drop'].mean():>8.3f}%")
    print(f"  최소:     {df_short['low_drop'].min():>8.3f}%")

    # 지정가 권장
    short_limit = df_short['high_rise'].mean() * 0.5
    print(f"\n✅ 지정가 권장: Open {short_limit:+.3f}% (High 평균의 50%)")
    print(f"   → 약 50% 확률로 체결 예상")

print("\n" + "="*80)
print("✅ 분석 완료!")
print("="*80)

# CSV 저장
df_entry.to_csv('entry_ohl_analysis.csv', index=False)
print("\nCSV 저장: entry_ohl_analysis.csv")
