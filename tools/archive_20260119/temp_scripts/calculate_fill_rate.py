"""지정가 체결률 정확한 계산

롱: Low <= offset (이하 전체 체결)
숏: High >= offset (이상 전체 체결)
"""

import pandas as pd

# CSV 로드
df = pd.read_csv('entry_ohl_analysis.csv')

long_df = df[df['side'] == 'Long']
short_df = df[df['side'] == 'Short']

print("="*80)
print("지정가 체결률 정확한 계산")
print("="*80)

print(f"\n총 거래 수:")
print(f"  Long:  {len(long_df):,}개")
print(f"  Short: {len(short_df):,}개")

# 지정가 오프셋 목록
offsets = [
    -0.001, -0.002, -0.005, -0.01, -0.015, -0.02, -0.03, -0.05, -0.1
]

print("\n" + "="*80)
print("롱 지정가 체결률 (Low <= offset)")
print("="*80)

for offset in offsets:
    # Low가 offset 이하인 경우 모두 체결
    filled = (long_df['low_drop'] <= offset).sum()
    fill_rate = filled / len(long_df) * 100
    print(f"\nOpen {offset:+.3f}% 지정가:")
    print(f"  체결: {filled:,}개 / {len(long_df):,}개")
    print(f"  체결률: {fill_rate:.1f}%")

print("\n" + "="*80)
print("숏 지정가 체결률 (High >= offset)")
print("="*80)

# 양수 오프셋으로 변환
short_offsets = [abs(o) for o in offsets]

for offset in short_offsets:
    # High가 offset 이상인 경우 모두 체결
    filled = (short_df['high_rise'] >= offset).sum()
    fill_rate = filled / len(short_df) * 100
    print(f"\nOpen {offset:+.3f}% 지정가:")
    print(f"  체결: {filled:,}개 / {len(short_df):,}개")
    print(f"  체결률: {fill_rate:.1f}%")

# 비교표
print("\n" + "="*80)
print("롱/숏 대칭 비교")
print("="*80)
print(f"\n{'오프셋':>10} | {'롱 체결률':>10} | {'숏 체결률':>10} | {'차이':>10}")
print("-"*80)

for offset in offsets:
    long_filled = (long_df['low_drop'] <= offset).sum() / len(long_df) * 100
    short_filled = (short_df['high_rise'] >= abs(offset)).sum() / len(short_df) * 100
    diff = short_filled - long_filled
    print(f"{offset:+.3f}% | {long_filled:>9.1f}% | {short_filled:>9.1f}% | {diff:+9.1f}%p")

print("\n" + "="*80)
print("분석 완료")
print("="*80)
