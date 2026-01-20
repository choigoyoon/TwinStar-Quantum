"""Low 하락 분포 확인 (롱/숏 공통)

롱/숏 모두 Low가 Open보다 얼마나 떨어지는지 분석
→ 지정가 주문 최적 가격 결정
"""

import pandas as pd

# CSV 로드
df = pd.read_csv('entry_ohl_analysis.csv')

print("="*80)
print("Low 하락 분포 분석 (롱/숏 공통)")
print("="*80)

# Long 분석
long_df = df[df['side'] == 'Long']
print(f"\n[Long 포지션] ({len(long_df)}개)")
print("-"*80)

# Low < Open인 경우 (유리)
low_lt_open = (long_df['low_drop'] < 0).sum()
low_eq_open = (long_df['low_drop'] == 0).sum()
low_gt_open = (long_df['low_drop'] > 0).sum()

print(f"Low < Open (유리): {low_lt_open:,}개 ({low_lt_open/len(long_df)*100:.2f}%)")
print(f"Low = Open (동일): {low_eq_open:,}개 ({low_eq_open/len(long_df)*100:.2f}%)")
print(f"Low > Open (불리): {low_gt_open:,}개 ({low_gt_open/len(long_df)*100:.2f}%)")

# Short 분석
short_df = df[df['side'] == 'Short']
print(f"\n[Short 포지션] ({len(short_df)}개)")
print("-"*80)

# Low < Open인 경우 (유리) - 롱과 동일!
low_lt_open_s = (short_df['low_drop'] < 0).sum()
low_eq_open_s = (short_df['low_drop'] == 0).sum()
low_gt_open_s = (short_df['low_drop'] > 0).sum()

print(f"Low < Open (유리): {low_lt_open_s:,}개 ({low_lt_open_s/len(short_df)*100:.2f}%)")
print(f"Low = Open (동일): {low_eq_open_s:,}개 ({low_eq_open_s/len(short_df)*100:.2f}%)")
print(f"Low > Open (불리): {low_gt_open_s:,}개 ({low_gt_open_s/len(short_df)*100:.2f}%)")

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

print(f"\n[Short Low 분포 히스토그램 - 초세밀 분석 (0.001% 단위)]")
print("-"*80)
for i in range(len(bins)-1):
    if i == 11:  # 0% (O=L) 케이스
        count = (short_df['low_drop'] == 0).sum()
    else:
        count = ((short_df['low_drop'] >= bins[i]) & (short_df['low_drop'] < bins[i+1])).sum()
    pct = count / len(short_df) * 100
    bar = '#' * int(pct)
    print(f"{bin_labels[i]:>17}: {bar} {count:,}개 ({pct:.1f}%)")

# 체결률 계산
print("\n" + "="*80)
print("지정가 체결률 예측 (Low 하락 기준)")
print("="*80)

offsets = [-0.001, -0.002, -0.005, -0.01, -0.02, -0.05, -0.1]
for offset in offsets:
    long_fill = (long_df['low_drop'] <= offset).sum() / len(long_df) * 100
    short_fill = (short_df['low_drop'] <= offset).sum() / len(short_df) * 100
    print(f"\nOpen {offset:+.3f}%:")
    print(f"  Long  체결률: {long_fill:>5.1f}% ({int(long_fill * len(long_df) / 100):,}/{len(long_df):,})")
    print(f"  Short 체결률: {short_fill:>5.1f}% ({int(short_fill * len(short_df) / 100):,}/{len(short_df):,})")

print("\n" + "="*80)
print("분석 완료")
print("="*80)
