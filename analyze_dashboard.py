from pathlib import Path
import re
import sys
import io

# Ensure plain output for terminal readability
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = Path(r'C:\매매전략')
gui = base / 'GUI'

print("=" * 70)
print("Dashboard 안정성 심층 체크")
print("=" * 70)

# 1. trading_dashboard.py 존재 및 기본 분석
dashboard = gui / 'trading_dashboard.py'
if not dashboard.exists():
    print("X trading_dashboard.py 없음!")
else:
    code = dashboard.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    print(f"O trading_dashboard.py ({len(lines)}줄)")

    # 2. Import 오류 가능성
    print("\n[1] Import 구문 체크")
    imports = []
    for i, line in enumerate(lines):
        if line.strip().startswith('from ') or line.strip().startswith('import '):
            imports.append((i+1, line.strip()[:60]))
    
    print(f"  총 {len(imports)}개 import")
    
    # 위험한 import 패턴 (core/exchanges 순환 참조 등)
    for ln, imp in imports:
        if 'core.' in imp or 'exchanges.' in imp:
            print(f"  L{ln}: {imp}")

    # 3. 스레드/비동기 관련
    print("\n[2] 스레드/비동기 체크")
    thread_patterns = ['QThread', 'threading', 'Thread', 'async ', 'await ', 'Worker']
    for pat in thread_patterns:
        if pat in code:
            print(f"  O {pat} 사용")
        else:
            print(f"  X {pat} 없음")

    # 4. UI 블로킹 가능 코드
    print("\n[3] UI 블로킹 위험 코드")
    blocking = []
    for i, line in enumerate(lines):
        # API 호출이 UI 스레드에서 직접 실행되는지 (단축판단)
        if 'get_balance' in line or 'get_position' in line or 'fetch_' in line:
            # QThread 내부인지 확인 (매우 단순화된 로직)
            context = '\n'.join(lines[max(0,i-15):i])
            if 'Worker' not in context and 'run(self)' not in context and 'QThread' not in context:
                blocking.append((i+1, line.strip()[:50]))
        
        # time.sleep UI 스레드
        if 'time.sleep' in line:
            context = '\n'.join(lines[max(0,i-10):i])
            if 'Worker' not in context and 'Thread' not in context:
                blocking.append((i+1, f"time.sleep: {line.strip()[:40]}"))
    
    if blocking:
        print(f"  [!] {len(blocking)}개 발견:")
        for ln, desc in blocking[:15]:
            print(f"    L{ln}: {desc}")
    else:
        print("  O 없음")

    # 5. 시그널-슬롯 연결 체크
    print("\n[4] 시그널-슬롯 연결")
    connects = re.findall(r'(\w+)\.connect\((\w+)\)', code)
    print(f"  총 {len(connects)}개 연결")
    
    # 6. 예외 처리
    print("\n[5] 예외 처리")
    try_count = code.count('try:')
    except_count = code.count('except')
    except_pass = len(re.findall(r'except.*:\s*\n\s*pass', code))
    
    print(f"  try: {try_count}개")
    print(f"  except: {except_count}개")
    print(f"  except: pass: {except_pass}개 [!]" if except_pass > 0 else f"  except: pass: 0개 O")

    # 7. None 체크 없는 위험 호출
    print("\n[6] None 체크 없는 호출")
    dangerous = []
    for i, line in enumerate(lines):
        # self.xxx.method() 패턴
        match = re.search(r'self\.(bot|exchange|manager|client|session)\.(\w+)\(', line)
        if match:
            prev = '\n'.join(lines[max(0,i-3):i])
            if 'is not None' not in prev and f'if self.{match.group(1)}' not in prev:
                dangerous.append((i+1, f"self.{match.group(1)}.{match.group(2)}()"))
    
    if dangerous:
        print(f"  [!] {len(dangerous)}개:")
        for ln, desc in dangerous[:15]:
            print(f"    L{ln}: {desc}")
    else:
        print("  O 없음")

    # 8. 타이머/주기적 업데이트
    print("\n[7] 타이머/주기적 업데이트")
    if 'QTimer' in code:
        timers = re.findall(r'QTimer|setInterval|timeout\.connect', code)
        print(f"  O QTimer 사용 ({len(timers)}개)")
    else:
        print("  X QTimer 없음")

    # 9. 거래소 루프
    print("\n[8] 거래소 순회 로직")
    exchange_loops = re.findall(r'for\s+\w+\s+in\s+.*exchange', code, re.I)
    if exchange_loops:
        print(f"  O 거래소 순회 있음")
    else:
        print("  [!] 거래소 순회 없음")

print("\n" + "=" * 70)
print("검증 완료")
print("=" * 70)
