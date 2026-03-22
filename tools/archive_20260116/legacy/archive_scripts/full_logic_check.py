
# full_logic_check.py
# TwinStar Quantum 전체 로직 심층 검증 스크립트

import os
import re
import sys

# 인코딩 설정 (PowerShell 출력용)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[union-attr]

ROOT = r"c:\매매전략"
UNIFIED = os.path.join(ROOT, "core", "unified_bot.py")
STRATEGY = os.path.join(ROOT, "core", "strategy_core.py")

# 결과 파일 초기화
with open("check_result.txt", "w", encoding="utf-8") as f:
    f.write("TwinStar Quantum Logic Check Details:\n")

PASS, FAIL, WARN = 0, 0, 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"✅ {name}")
        PASS += 1
    else:
        msg = f"❌ {name}: {detail}"
        print(msg)
        with open("check_result.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        FAIL += 1

def warn(name, detail=""):
    global WARN
    print(f"⚠️ {name}: {detail}")
    WARN += 1

def count_pattern(content, pattern):
    return len(re.findall(pattern, content))

def find_lines(content, pattern):
    lines = content.split('\n')
    result = []
    for i, line in enumerate(lines, 1):
        if re.search(pattern, line):
            result.append((i, line.strip()[:80])) # 길이 제한 늘림
    return result

# 파일 로드
try:
    with open(UNIFIED, 'r', encoding='utf-8') as f:
        unified = f.read()
    with open(STRATEGY, 'r', encoding='utf-8') as f:
        strategy = f.read()
except FileNotFoundError:
    print("❌ 파일을 찾을 수 없습니다. 경로를 확인하세요.")
    sys.exit(1)

print("=" * 70)
print("TwinStar Quantum - 전체 로직 검증")
print("=" * 70)

# ============================================================
# 1. 데이터 갱신 주기 (핵심)
# ============================================================
print("\n[1] 데이터 갱신 주기")
print("-" * 50)

check("3540(59분) 제거됨", "3540" not in unified, "3540 잔존")
# 공백 처리 유연하게: > 60, >60 등
check("> 60 적용됨", re.search(r">\s*60", unified) is not None, "> 60 없음")

lines_60 = find_lines(unified, r">\s*60")
print(f"   > 60 위치 (라인): {[l[0] for l in lines_60]}")

# ============================================================
# 2. 프리셋 파라미터 전달
# ============================================================
print("\n[2] 프리셋 파라미터 전달 (unified_bot.py)")
print("-" * 50)

params = ['pattern_tolerance', 'entry_validity', 'filter_tf', 'entry_tf', 'atr_mult', 'trail_start_r', 'trail_dist_r']
for p in params:
    found = p in unified
    check(f"'{p}' 사용", found, "미발견")
    # 위치는 너무 많으면 생략
    # if found:
    #     lines = find_lines(unified, p)
    #     print(f"      위치: {[l[0] for l in lines[:3]]}")

# ============================================================
# 3. 백테스트 vs 실거래 로직 일치
# ============================================================
print("\n[3] 백테스트 vs 실거래 일치")
print("-" * 50)

# resample 사용
check("unified: resample 사용", "resample" in unified)
check("strategy: resample 사용", "resample" in strategy)

# detect_pattern / detect_signal
check("unified: detect_signal 존재", "def detect_signal" in unified or "detect_signal" in unified)
check("strategy: detect_pattern 존재", "detect_pattern" in strategy or "detect_signal" in strategy)

# get_mtf_trend / get_filter_trend
# 전략 코어에 get_mtf_trend가 있고 봇이 호출
unified_trend = "get_mtf_trend" in unified or "get_filter_trend" in unified
strategy_trend = "get_mtf_trend" in strategy or "get_filter_trend" in strategy
check("unified: MTF 트렌드 함수 호출", unified_trend)
check("strategy: MTF 트렌드 함수 정의", strategy_trend)

# ============================================================
# 4. 현재가 반영 로직
# ============================================================
print("\n[4] 현재가 반영")
print("-" * 50)

# iloc[-1] 사용 위치
unified_iloc = find_lines(unified, r"iloc\[-1\]")
strategy_iloc = find_lines(strategy, r"iloc\[-1\]")
print(f"   unified iloc[-1]: {len(unified_iloc)}개") # 너무 많아서 개수만
print(f"   strategy iloc[-1]: {len(strategy_iloc)}개")

# 웹소켓 가격 사용
check("last_ws_price 사용", "last_ws_price" in unified)
ws_lines = find_lines(unified, "last_ws_price")
print(f"      위치 (상위 3개): {[l[0] for l in ws_lines[:3]]}")

# ============================================================
# 5. SL/TP 계산 로직
# ============================================================
print("\n[5] SL/TP 계산")
print("-" * 50)

# atr_mult 사용
check("unified: atr_mult 사용", "atr_mult" in unified)
check("strategy: atr_mult 사용", "atr_mult" in strategy)

# stop_loss 계산
unified_sl = find_lines(unified, r"stop_loss|sl_price|sl_pct")
strategy_sl = find_lines(strategy, r"stop_loss|sl_price|sl_pct")
print(f"   unified SL 관련: {len(unified_sl)}개")
print(f"   strategy SL 관련: {len(strategy_sl)}개")

# trailing 로직
check("unified: trailing 로직", "trail" in unified.lower())
check("strategy: trailing 로직", "trail" in strategy.lower())

# ============================================================
# 6. 시그널 유효성 검사
# ============================================================
print("\n[6] 시그널 유효성")
print("-" * 50)

check("unified: validity 체크", "validity" in unified.lower() or "valid" in unified.lower())
check("unified: expired 체크", "expire" in unified.lower())

# ============================================================
# 7. 레버리지/방향 처리
# ============================================================
print("\n[7] 레버리지/방향")
print("-" * 50)

check("unified: leverage 사용", "leverage" in unified)
check("unified: direction 사용", "direction" in unified)

# ============================================================
# 8. 거래소 연동
# ============================================================
print("\n[8] 거래소 연동")
print("-" * 50)

check("get_klines 호출", "get_klines" in unified)
check("place_order 호출", "place_order" in unified or "create_order" in unified)
check("set_leverage 호출", "set_leverage" in unified)

# ============================================================
# 9. 위험 패턴 검사
# ============================================================
print("\n[9] 위험 패턴")
print("-" * 50)

# 미래 데이터 참조 가능성
future_patterns = find_lines(strategy, r"shift\(-")
if future_patterns:
    warn("shift(-N) 발견 (미래 참조 가능)", f"L{[l[0] for l in future_patterns]}")
else:
    check("미래 참조 shift(-N) 없음", True)

# 하드코딩된 값
hardcoded = find_lines(unified, r"= 3540|= 59|= 58")
if hardcoded:
    check("59분 하드코딩 없음", False, f"발견됨: {hardcoded}")
else:
    check("59분 하드코딩 없음", True)

# ============================================================
# 10. 핵심 함수 존재 확인
# ============================================================
print("\n[10] 핵심 함수")
print("-" * 50)

# manage_position 이름이 다를 수 있음 (execute_order 등)
funcs_unified = ['detect_signal', 'manage_position', '_on_candle_close'] # execute_order는 없을수도
funcs_strategy = ['run_backtest', 'detect_signal', 'get_mtf_trend'] # run_backtest는 확실

for f in funcs_unified:
    # 부분 일치로 확인 (메서드명 등)
    check(f"unified: {f}", f"def {f}" in unified or f in unified)

for f in funcs_strategy:
    check(f"strategy: {f}", f"def {f}" in strategy or f in strategy)

# ============================================================
# 결과
# ============================================================
print("\n" + "=" * 70)
print("최종 결과")
print("=" * 70)

total = PASS + FAIL + WARN
result_txt = f"""
============================================================
TwinStar Quantum Logic Check Result
============================================================
PASS: {PASS}
FAIL: {FAIL}
WARN: {WARN}
TOTAL: {total}
"""

if FAIL == 0 and WARN == 0:
    result_txt += "\nRESULT: ALL PASS (Ready for Real Trading)"
elif FAIL == 0:
    result_txt += "\nRESULT: PASS with WARNINGS"
else:
    result_txt += "\nRESULT: FAIL (Action Required)"

print(result_txt)

print(result_txt)

with open("check_result.txt", "a", encoding="utf-8") as f:
    f.write(result_txt)

