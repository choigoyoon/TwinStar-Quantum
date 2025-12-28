from pathlib import Path
import re
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 70)
print("전체 코드베이스 문제점 스캔")
print("=" * 70)

issues = []

# 1. DataFrame 위험 패턴
print("\n[1] DataFrame 위험 패턴 (or/and 연산)")
for f in base.rglob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # Check for likely dataframe empty checks combined with logic operators which are ambiguous in pandas
            if re.search(r'if\s+\w+\s+(or|and)\s+\w+\.empty', line):
                if 'is None' not in line:
                    print(f"  {f.name} L{i+1}: {line.strip()[:60]}")
                    issues.append(('DataFrame', f.name, i+1))
    except: pass

# 2. .get() 호출 (객체 vs 딕셔너리)
print("\n[2] Signal/객체에 .get() 호출")
for f in base.rglob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'signal.get(' in code.lower() or "signal['direction']" in code:
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if re.search(r'signal\.get\(|signal\[', line, re.I):
                    # Filter out likely safe dict usages if known, but for now report all to be safe
                    print(f"  {f.name} L{i+1}: {line.strip()[:60]}")
                    issues.append(('Signal접근', f.name, i+1))
    except: pass

# 3. 선물 거래소 positionIdx 누락
print("\n[3] 선물 거래소 positionIdx 누락")
for f in (base / 'exchanges').glob('*_exchange.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        is_futures = 'linear' in code.lower() or 'swap' in code.lower() or 'futures' in code.lower() or 'category' in code.lower()
        has_idx = 'positionIdx' in code or 'positionSide' in code or 'posSide' in code
        if is_futures and not has_idx:
            print(f"  ❌ {f.name}: 선물인데 positionIdx/Side 없음")
            issues.append(('PositionIdx', f.name, 0))
    except: pass

# 4. except: pass (에러 무시)
print("\n[4] except: pass (에러 삼킴)")
for f in base.rglob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        # Simple regex for except followed immediately by pass, potentially on next line
        if re.search(r'except.*:\s*(\n\s*)?pass', code):
            matches = re.findall(r'except.*:\s*(\n\s*)?pass', code)
            print(f"  {f.name}: {len(matches)}개")
            issues.append(('ExceptPass', f.name, len(matches)))
    except: pass

# 5. 하드코딩된 경로
print("\n[5] 하드코딩된 경로")
for f in base.rglob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'C:\\' in code or 'C:/' in code:
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'C:\\' in line or 'C:/' in line:
                    if '#' not in line.split('C:')[0]:  # 주석 제외 attempt
                         # Also exclude this script itself
                        if f.name != 'diagnose_all_issues.py':
                            print(f"  {f.name} L{i+1}: {line.strip()[:50]}")
                            issues.append(('HardPath', f.name, i+1))
                            break
    except: pass

# 6. time.sleep in async
print("\n[6] async 함수 내 time.sleep")
for f in base.rglob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'async def' in code and 'time.sleep' in code:
            print(f"  ⚠️ {f.name}: async + time.sleep 혼용 가능성")
            issues.append(('AsyncSleep', f.name, 0))
    except: pass

# 7. 모듈 import 경로 문제
print("\n[7] core.updater 등 import 경로")
for f in base.rglob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'from core.updater' in code or 'import core.updater' in code:
            print(f"  {f.name}: core.updater import 발견")
            issues.append(('ImportPath', f.name, 0))
    except: pass

# 8. 현물 Short 차단 누락
print("\n[8] 현물 Short 차단 로직")
for f_path in [base / 'core/unified_bot.py', base / 'core/strategy_core.py']:
    if f_path.exists():
        code = f_path.read_text(encoding='utf-8', errors='ignore')
        has_spot_block = 'spot' in code.lower() and 'short' in code.lower() and ('block' in code.lower() or 'pass' in code.lower() or 'return' in code.lower())
        print(f"  {f_path.name}: {'✅ 있음' if has_spot_block else '❌ 없음'}")
        if not has_spot_block:
            issues.append(('SpotShort', f_path.name, 0))

# 요약
print("\n" + "=" * 70)
print(f"총 {len(issues)}개 잠재적 문제 발견")
print("=" * 70)

by_type = {}
for t, f, l in issues:
    by_type[t] = by_type.get(t, 0) + 1
for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}개")
