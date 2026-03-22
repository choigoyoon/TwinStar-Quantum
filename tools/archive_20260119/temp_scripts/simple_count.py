"""간단한 체결률 계산"""
import sys

long_count = 0
short_count = 0

# 롱 카운터 (Low <= offset인 개수)
long_thresholds = {
    -0.001: 0, -0.002: 0, -0.005: 0, -0.01: 0, -0.02: 0, -0.05: 0, -0.1: 0
}

# 숏 카운터 (High >= offset인 개수)
short_thresholds = {
    0.001: 0, 0.002: 0, 0.005: 0, 0.01: 0, 0.02: 0, 0.05: 0, 0.1: 0
}

try:
    with open('entry_ohl_analysis.csv', 'r') as f:
        next(f)  # 헤더 스킵

        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 6:
                continue

            side = parts[0]
            low_drop = float(parts[4])
            high_rise = float(parts[5])

            if side == 'Long':
                long_count += 1
                for threshold in long_thresholds:
                    if low_drop <= threshold:
                        long_thresholds[threshold] += 1
            else:
                short_count += 1
                for threshold in short_thresholds:
                    if high_rise >= threshold:
                        short_thresholds[threshold] += 1

    print("="*80)
    print("체결률 분석 결과")
    print("="*80)
    print(f"\n총 거래: Long {long_count:,}개 / Short {short_count:,}개")

    print("\n[롱 체결률 - Low <= offset]")
    print("-"*80)
    for offset in sorted(long_thresholds.keys()):
        count = long_thresholds[offset]
        rate = count / long_count * 100
        print(f"{offset:+.3f}%: {count:>5,}개 ({rate:>5.1f}%)")

    print("\n[숏 체결률 - High >= offset]")
    print("-"*80)
    for offset in sorted(short_thresholds.keys()):
        count = short_thresholds[offset]
        rate = count / short_count * 100
        print(f"{offset:+.3f}%: {count:>5,}개 ({rate:>5.1f}%)")

    print("\n[롱/숏 비교]")
    print("-"*80)
    print(f"{'오프셋':>10} | {'롱 체결률':>10} | {'숏 체결률':>10} | {'차이':>10}")
    print("-"*80)
    for i, (long_off, short_off) in enumerate([
        (-0.001, 0.001), (-0.002, 0.002), (-0.005, 0.005),
        (-0.01, 0.01), (-0.02, 0.02), (-0.05, 0.05), (-0.1, 0.1)
    ]):
        long_rate = long_thresholds[long_off] / long_count * 100
        short_rate = short_thresholds[short_off] / short_count * 100
        diff = short_rate - long_rate
        print(f"±{abs(long_off):.3f}% | {long_rate:>9.1f}% | {short_rate:>9.1f}% | {diff:+9.1f}%p")

    print("\n" + "="*80)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
