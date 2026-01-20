"""초세밀 체결률 계산 (0.001% 단위)"""

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
print("초세밀 지정가 체결률 계산 (0.001% 단위)")
print("="*80)

print(f"\n총 거래 수:")
print(f"  Long:  {len(long_low_drops):,}개")
print(f"  Short: {len(short_high_rises):,}개")

# 0.001% 단위 오프셋
offsets = [
    -0.001, -0.002, -0.003, -0.004, -0.005,
    -0.006, -0.007, -0.008, -0.009, -0.01,
    -0.015, -0.02, -0.025, -0.03, -0.04, -0.05,
    -0.06, -0.07, -0.08, -0.09, -0.1
]

print("\n" + "="*80)
print("롱 지정가 체결률 (Low <= offset)")
print("="*80)
print(f"\n{'지정가':>12} | {'체결수':>10} | {'체결률':>8} | {'누적 바':>40}")
print("-"*80)

for offset in offsets:
    filled = sum(1 for x in long_low_drops if x <= offset)
    fill_rate = filled / len(long_low_drops) * 100
    bar = '#' * int(fill_rate / 2.5)  # 40칸 기준 (100% = 40칸)
    print(f"{offset:+.3f}% | {filled:>9,}개 | {fill_rate:>7.1f}% | {bar}")

print("\n" + "="*80)
print("숏 지정가 체결률 (High >= offset)")
print("="*80)
print(f"\n{'지정가':>12} | {'체결수':>10} | {'체결률':>8} | {'누적 바':>40}")
print("-"*80)

for offset in [abs(o) for o in offsets]:
    filled = sum(1 for x in short_high_rises if x >= offset)
    fill_rate = filled / len(short_high_rises) * 100
    bar = '#' * int(fill_rate / 2.5)
    print(f"{offset:+.3f}% | {filled:>9,}개 | {fill_rate:>7.1f}% | {bar}")

# 롱/숏 대칭 비교표
print("\n" + "="*80)
print("롱/숏 대칭 비교 (동일 절대값 오프셋)")
print("="*80)
print(f"\n{'오프셋':>12} | {'롱 체결':>10} | {'숏 체결':>10} | {'차이':>10} | {'비율':>8}")
print("-"*80)

for offset in offsets[:16]:  # -0.001 ~ -0.05까지만
    long_fill = sum(1 for x in long_low_drops if x <= offset) / len(long_low_drops) * 100
    short_fill = sum(1 for x in short_high_rises if x >= abs(offset)) / len(short_high_rises) * 100
    diff = short_fill - long_fill
    ratio = short_fill / long_fill if long_fill > 0 else 0
    print(f"{offset:+.3f}% | {long_fill:>9.1f}% | {short_fill:>9.1f}% | {diff:+9.1f}%p | {ratio:>7.2f}x")

# 권장 지정가 찾기
print("\n" + "="*80)
print("권장 지정가 (체결률 기준)")
print("="*80)

# 롱: 50%, 60%, 70% 체결률 달성 오프셋 찾기
target_rates = [50, 60, 70, 80]
print("\n[Long 권장 지정가]")
print(f"{'목표 체결률':>15} | {'권장 오프셋':>15} | {'실제 체결률':>15}")
print("-"*60)

for target in target_rates:
    best_offset = None
    best_diff = 999
    for offset in offsets:
        filled = sum(1 for x in long_low_drops if x <= offset)
        fill_rate = filled / len(long_low_drops) * 100
        diff = abs(fill_rate - target)
        if diff < best_diff:
            best_diff = diff
            best_offset = offset
            best_rate = fill_rate
    print(f"{target:>14}% | {best_offset:>+14.3f}% | {best_rate:>14.1f}%")

print("\n[Short 권장 지정가]")
print(f"{'목표 체결률':>15} | {'권장 오프셋':>15} | {'실제 체결률':>15}")
print("-"*60)

for target in target_rates:
    best_offset = None
    best_diff = 999
    for offset in [abs(o) for o in offsets]:
        filled = sum(1 for x in short_high_rises if x >= offset)
        fill_rate = filled / len(short_high_rises) * 100
        diff = abs(fill_rate - target)
        if diff < best_diff:
            best_diff = diff
            best_offset = offset
            best_rate = fill_rate
    print(f"{target:>14}% | {best_offset:>+14.3f}% | {best_rate:>14.1f}%")

print("\n" + "="*80)
print("완료!")
print("="*80)
