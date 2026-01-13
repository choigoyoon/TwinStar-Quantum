from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 70)
print("전체 코드베이스 .get() 호출 안전성 검사")
print("=" * 70)

issues = []

# 1. 모든 .get() 호출에서 타입 체크 없는 것
print("\n[1] .get() 호출 전 타입 체크 없음")
for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            # xxx.get( 패턴 찾기
            if '.get(' in line and 'isinstance' not in line:
                # 변수명 추출
                match = re.search(r'(\w+)\.get\(', line)
                if match:
                    var = match.group(1)
                    # 이전 5줄에서 isinstance 체크 있는지
                    prev_lines = '\n'.join(lines[max(0,i-5):i])
                    if f'isinstance({var}' not in prev_lines and f'{var} is not None' not in prev_lines:
                        # dict, self, cls 등은 제외
                        if var not in ['self', 'cls', 'dict', 'os', 'sys', 'config', 'params', 'kwargs', 'options']:
                            issues.append((f.name, i+1, var, line.strip()[:50]))
    except Exception:

        pass

print(f"\n발견: {len(issues)}개")
for name, ln, var, code in issues[:20]:
    print(f"  {name} L{ln}: {var}.get() - {code}")

if len(issues) > 20:
    print(f"  ... 외 {len(issues)-20}개")

# 2. place_order 계열 반환값 처리
print("\n" + "=" * 70)
print("[2] 주문 함수 반환값 타입 불일치")
print("=" * 70)

for f in (base / 'exchanges').glob('*_exchange.py'):
    code = f.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    returns = {'True': 0, 'False': 0, 'dict': 0, 'None': 0}
    
    in_order_func = False
    for i, line in enumerate(lines):
        if 'def place' in line or 'def create_order' in line:
            in_order_func = True
        if in_order_func:
            if 'return True' in line:
                returns['True'] += 1
            if 'return False' in line:
                returns['False'] += 1
            if 'return {' in line or 'return result' in line:
                returns['dict'] += 1
            if 'return None' in line:
                returns['None'] += 1
            if line.strip().startswith('def ') and 'place' not in line:
                in_order_func = False
    
    if sum(returns.values()) > 0:
        print(f"\n{f.name}:")
        for k, v in returns.items():
            if v > 0:
                print(f"  return {k}: {v}회")

# 3. API 응답 직접 접근 (.get 없이 ['key'])
print("\n" + "=" * 70)
print("[3] API 응답 직접 접근 (KeyError 위험)")
print("=" * 70)

count3 = 0
for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            # response['key'] or result['key'] 패턴
            if re.search(r"(response|result|data|order)\[['\"]", line):
                if '.get(' not in line:
                    prev_text = '\n'.join(lines[max(0,i-2):i+1])
                    if 'try' not in prev_text:
                        if count3 < 15:
                            print(f"  {f.name} L{i+1}: {line.strip()[:50]}")
                        count3 += 1
    except Exception:

        pass

if count3 > 15:
    print(f"  ... 외 {count3-15}개")

# 4. None 체크 없이 메서드 호출
print("\n" + "=" * 70)
print("[4] None 체크 없이 메서드 호출 (AttributeError 위험)")
print("=" * 70)

critical_files = ['core/unified_bot.py', 'core/strategy_core.py']
for cf in critical_files:
    f = base / cf
    if not f.exists():
        continue
    code = f.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    count = 0
    for i, line in enumerate(lines):
        # self.xxx.method() 중 xxx가 None일 수 있는 것
        match = re.search(r'self\.(\w+)\.(\w+)\(', line)
        if match and count < 5:
            var = match.group(1)
            # None 가능한 변수들
            if var in ['session', 'exchange', 'ws', 'ws_handler', 'position', 'order']:
                prev = '\n'.join(lines[max(0,i-3):i])
                if f'self.{var} is not None' not in prev and f'if self.{var}' not in prev:
                    print(f"  {cf} L{i+1}: self.{var}.{match.group(2)}()")
                    count += 1

print("\n" + "=" * 70)
print(f"총 .get() 안전성 문제: {len(issues)}개")
print("=" * 70)
