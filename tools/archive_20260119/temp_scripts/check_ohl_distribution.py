"""O-H-L 분포 확인

O = L (Long) 또는 O = H (Short)인 경우가 얼마나 되는지 확인
"""

import pandas as pd

# CSV 로드
df = pd.read_csv('entry_ohl_analysis.csv')

print("="*80)
print("O-H-L 분포 분석")
print("="*80)

# Long 분석
long_df = df[df['side'] == 'Long']
print(f"\n[Long 포지션] ({len(long_df)}개)")
print("-"*80)

# Low = Open인 경우
low_eq_open = (long_df['low_drop'] == 0).sum()
low_lt_open = (long_df['low_drop'] < 0).sum()
low_gt_open = (long_df['low_drop'] > 0).sum()

print(f"Low < Open (유리): {low_lt_open:,}개 ({low_lt_open/len(long_df)*100:.2f}%)")
print(f"Low = Open (동일): {low_eq_open:,}개 ({low_eq_open/len(long_df)*100:.2f}%)")
print(f"Low > Open (불리): {low_gt_open:,}개 ({low_gt_open/len(long_df)*100:.2f}%)")

print(f"\n상세 분포:")
print(f"  Low < Open - 0.1%: {(long_df['low_drop'] < -0.1).sum():,}개")
print(f"  Low < Open - 0.05%: {(long_df['low_drop'] < -0.05).sum():,}개")
print(f"  -0.05% ≤ Low < 0%: {((long_df['low_drop'] >= -0.05) & (long_df['low_drop'] < 0)).sum():,}개")

# Short 분석
short_df = df[df['side'] == 'Short']
print(f"\n[Short 포지션] ({len(short_df)}개)")
print("-"*80)

# High = Open인 경우
high_eq_open = (short_df['high_rise'] == 0).sum()
high_gt_open = (short_df['high_rise'] > 0).sum()
high_lt_open = (short_df['high_rise'] < 0).sum()

print(f"High > Open (유리): {high_gt_open:,}개 ({high_gt_open/len(short_df)*100:.2f}%)")
print(f"High = Open (동일): {high_eq_open:,}개 ({high_eq_open/len(short_df)*100:.2f}%)")
print(f"High < Open (불리): {high_lt_open:,}개 ({high_lt_open/len(short_df)*100:.2f}%)")

print(f"\n상세 분포:")
print(f"  High > Open + 0.1%: {(short_df['high_rise'] > 0.1).sum():,}개")
print(f"  High > Open + 0.05%: {(short_df['high_rise'] > 0.05).sum():,}개")
print(f"  0% < High ≤ 0.05%: {((short_df['high_rise'] > 0) & (short_df['high_rise'] <= 0.05)).sum():,}개")

# 극단값 확인
print(f"\n[극단값 분석]")
print("-"*80)
print(f"Long - 가장 유리한 진입 (최대 하락): {long_df['low_drop'].min():.3f}%")
print(f"Long - 가장 불리한 진입 (최대 상승): {long_df['low_drop'].max():.3f}%")
print(f"Short - 가장 유리한 진입 (최대 상승): {short_df['high_rise'].max():.3f}%")
print(f"Short - 가장 불리한 진입 (최대 하락): {short_df['high_rise'].min():.3f}%")

# 히스토그램 (초세밀 구간 - 0.001% 단위)
print(f"\n[Long Low 분포 히스토그램 - 초세밀 분석 (0.001% 단위)]")
print("-"*80)
bins = [-2, -0.5, -0.3, -0.2, -0.1, -0.05, -0.02, -0.01, -0.005, -0.002, -0.001, 0,
        0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.5, 5]
bin_labels = ['< -0.5%', '-0.5~-0.3%', '-0.3~-0.2%', '-0.2~-0.1%', '-0.1~-0.05%',
              '-0.05~-0.02%', '-0.02~-0.01%', '-0.01~-0.005%', '-0.005~-0.002%',
              '-0.002~-0.001%', '-0.001~0%', '0% (O=L)', '0~0.001%', '0.001~0.002%',
              '0.002~0.005%', '0.005~0.01%', '0.01~0.02%', '0.02~0.05%',
              '0.05~0.1%', '0.1~0.5%', '> 0.5%']

for i in range(len(bins)-1):
    if i == 11:  # 0% (O=L) 케이스
        count = (long_df['low_drop'] == 0).sum()
    else:
        count = ((long_df['low_drop'] >= bins[i]) & (long_df['low_drop'] < bins[i+1])).sum()
    pct = count / len(long_df) * 100
    bar = '#' * int(pct)
    print(f"{bin_labels[i]:>17}: {bar} {count:,}개 ({pct:.1f}%)")

print(f"\n[Short High 분포 히스토그램 - 초세밀 분석 (0.001% 단위)]")
print("-"*80)
for i in range(len(bins)-1):
    if i == 11:  # 0% (O=H) 케이스
        count = (short_df['high_rise'] == 0).sum()
    else:
        count = ((short_df['high_rise'] >= bins[i]) & (short_df['high_rise'] < bins[i+1])).sum()
    pct = count / len(short_df) * 100
    bar = '#' * int(pct)
    print(f"{bin_labels[i]:>17}: {bar} {count:,}개 ({pct:.1f}%)")

print("\n" + "="*80)
print("✅ 분석 완료!")
print("="*80)
