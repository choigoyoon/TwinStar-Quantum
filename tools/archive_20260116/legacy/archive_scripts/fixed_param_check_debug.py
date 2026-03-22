# fixed_param_check_debug.py
import os
import sys
import io

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[union-attr]

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
print("파라미터 일관성 정밀 검증")
print("=" * 60)

# 기준 파라미터
STANDARD_PARAMS = ['atr_mult', 'trail_start_r', 'trail_dist_r']

# 1. optimization_widget.py
print("\n[1] optimization_widget.py")
try:
    with open(os.path.join(ROOT, "GUI", "optimization_widget.py"), "r", encoding="utf-8") as f:
        opt = f.read()

    for p in STANDARD_PARAMS:
        condition = f"'{p}'" in opt or f"\"{p}\"" in opt
        check(f"{p} 키 존재", condition)
        if not condition:
            print(f"   -> 실제 코드에서 '{p}' 문자열을 찾을 수 없습니다.")

    # 구버전 사용 체크
    if "'atr_multiplier'" in opt:
        check("atr_multiplier 미사용", False)
        print("   -> 'atr_multiplier'가 여전히 코드에 남아있습니다.")
    else:
        check("atr_multiplier 미사용", True)
        
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    FAIL += 1

# 2. backtest_widget.py
print("\n[2] backtest_widget.py")
try:
    with open(os.path.join(ROOT, "GUI", "backtest_widget.py"), "r", encoding="utf-8") as f:
        bt = f.read()

    for p in STANDARD_PARAMS:
        condition = p in bt
        check(f"{p} 사용", condition)
        if not condition:
            print(f"   -> 실제 코드에서 '{p}' 문자열을 찾을 수 없습니다.")
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    FAIL += 1

# 3. strategy_core.py
print("\n[3] strategy_core.py")
try:
    with open(os.path.join(ROOT, "core", "strategy_core.py"), "r", encoding="utf-8") as f:
        strat = f.read()

    for p in STANDARD_PARAMS:
        condition = p in strat
        check(f"{p} 정의", condition)
        if not condition:
            print(f"   -> 실제 코드에서 '{p}' 문자열을 찾을 수 없습니다.")
except Exception as e:
    print(f"❌ 파일 읽기 실패: {e}")
    FAIL += 1

print("\n" + "=" * 60)
print(f"결과: PASS {PASS} / FAIL {FAIL}")
print("=" * 60)

if FAIL == 0:
    print("✅ 모든 검증 통과 - EXE 빌드 즉시 시작")
else:
    print("❌ 실패 항목 존재 - 디버깅 필요")
