# fixed_param_check.py
import os
import sys

# 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"c:\매매전략"
PASS, FAIL = 0, 0

def check(name, condition):
    global PASS, FAIL
    if condition:
        print(f"✅ {name}")
        PASS += 1
    else:
        print(f"❌ {name}")
        FAIL += 1

print("=" * 60)
print("파라미터 일관성 검증 (strategy_core 기준)")
print("=" * 60)

# 기준: strategy_core.py DEFAULT_PARAMS
STANDARD_PARAMS = ['atr_mult', 'trail_start_r', 'trail_dist_r', 'leverage', 'direction']

# 1. strategy_core.py (기준)
print("\n[1] strategy_core.py (기준)")
try:
    with open(os.path.join(ROOT, "core", "strategy_core.py"), "r", encoding="utf-8") as f:
        strat = f.read()

    for p in STANDARD_PARAMS:
        check(f"{p} 존재", p in strat)
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    FAIL += 1

# 2. optimization_widget.py
print("\n[2] optimization_widget.py")
try:
    with open(os.path.join(ROOT, "GUI", "optimization_widget.py"), "r", encoding="utf-8") as f:
        opt = f.read()

    for p in STANDARD_PARAMS:
        check(f"{p} 키 존재", f"'{p}'" in opt)
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    FAIL += 1

# 3. backtest_widget.py
print("\n[3] backtest_widget.py")
try:
    with open(os.path.join(ROOT, "GUI", "backtest_widget.py"), "r", encoding="utf-8") as f:
        bt = f.read()

    for p in ['atr_mult', 'trail_start_r', 'trail_dist_r']:
        check(f"{p} 사용", p in bt)
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    FAIL += 1

# 4. 구버전 파라미터 없는지 확인
print("\n[4] 구버전 파라미터 없음 확인")
# atr_multiplier 키가 없어야 함
check("optimization: atr_multiplier 없음", "'atr_multiplier'" not in opt) 
# 단순히 string matching하면 주석에 걸릴 수 있으니 주의. 여기선 단순 체크.

# 결과
print("\n" + "=" * 60)
print(f"결과: PASS {PASS} / FAIL {FAIL}")
print("=" * 60)

if FAIL == 0:
    print("✅ 모든 검증 통과 - EXE 빌드 가능")
else:
    print("❌ 실패 항목 수정 필요")
