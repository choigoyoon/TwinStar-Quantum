"""빠른 체결률 계산 (pandas 최소 버전)"""

# CSV 한 줄씩 읽어서 계산
long_low_drops = []
short_high_rises = []

with open('entry_ohl_analysis.csv', 'r') as f:
    # 헤더 건너뛰기
    next(f)

    for line in f:
        parts = line.strip().split(',')
        if len(parts) < 6:
            continue

        side = parts[0]
        low_drop = float(parts[4])
        high_rise = float(parts[5])

        if side == 'Long':
            long_low_drops.append(low_drop)
        else:  # Short
            short_high_rises.append(high_rise)

print("="*80)
print("지정가 체결률 계산")
print("="*80)

print(f"\n총 거래 수:")
print(f"  Long:  {len(long_low_drops):,}개")
print(f"  Short: {len(short_high_rises):,}개")

# 지정가 오프셋
offsets = [-0.001, -0.002, -0.005, -0.01, -0.015, -0.02, -0.03, -0.05, -0.1]

print("\n" + "="*80)
print("롱 지정가 체결률 (Low <= offset)")
print("="*80)

for offset in offsets:
    filled = sum(1 for x in long_low_drops if x <= offset)
    fill_rate = filled / len(long_low_drops) * 100
    print(f"\nOpen {offset:+.3f}% 지정가:")
    print(f"  체결: {filled:,}개 / {len(long_low_drops):,}개")
    print(f"  체결률: {fill_rate:.1f}%")

print("\n" + "="*80)
print("숏 지정가 체결률 (High >= offset)")
print("="*80)

for offset in [abs(o) for o in offsets]:
    filled = sum(1 for x in short_high_rises if x >= offset)
    fill_rate = filled / len(short_high_rises) * 100
    print(f"\nOpen {offset:+.3f}% 지정가:")
    print(f"  체결: {filled:,}개 / {len(short_high_rises):,}개")
    print(f"  체결률: {fill_rate:.1f}%")

# 비교표
print("\n" + "="*80)
print("롱/숏 대칭 비교")
print("="*80)
print(f"\n{'오프셋':>10} | {'롱 체결률':>10} | {'숏 체결률':>10} | {'차이':>10}")
print("-"*80)

for offset in offsets:
    long_fill = sum(1 for x in long_low_drops if x <= offset) / len(long_low_drops) * 100
    short_fill = sum(1 for x in short_high_rises if x >= abs(offset)) / len(short_high_rises) * 100
    diff = short_fill - long_fill
    print(f"{offset:+.3f}% | {long_fill:>9.1f}% | {short_fill:>9.1f}% | {diff:+9.1f}%p")

print("\n" + "="*80)
print("완료!")
print("="*80)
