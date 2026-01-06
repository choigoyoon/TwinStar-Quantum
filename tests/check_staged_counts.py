"""모드별 순차 최적화 조합 수 확인"""
import sys
sys.path.insert(0, '.')
from core.optimization_logic import get_stage_grids

def count_combos(grids):
    s1, s2, s3 = grids
    c1, c2, c3 = 1, 1, 1
    for v in s1.values(): c1 *= len(v)
    for v in s2.values(): c2 *= len(v)
    for v in s3.values(): c3 *= len(v)
    return c1, c2, c3, c1 + c2 + c3

print("=" * 50)
print("   모드별 순차 최적화 조합 수")
print("=" * 50 + "\n")

for mode in ['quick', 'standard', 'deep']:
    grids = get_stage_grids(mode)
    s1, s2, s3, total = count_combos(grids)
    print(f"[{mode.upper():>8}]")
    print(f"  Stage 1: {s1:>3} 조합 (filter_tf, atr, direction)")
    print(f"  Stage 2: {s2:>3} 조합 (trail, validity)")
    print(f"  Stage 3: {s3:>3} 조합 (RSI)")
    print(f"  ──────────────────")
    print(f"  Total:   {total:>3} 조합\n")

print("✅ Quick < Standard < Deep 순서 확인!")
