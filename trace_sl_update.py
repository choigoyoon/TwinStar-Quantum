"""실제 SL 업데이트 로직 추적 status"""
from pathlib import Path

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 실제 SL 업데이트 로직 추적")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# 1) manage_position 함수 전체 내용
print("\n[1] manage_position 함수 전체")
print("-" * 50)

in_func = False
func_lines = []
for i, line in enumerate(lines, 1):
    if 'def manage_position(' in line or 'def _manage_position(' in line:
        # Check if it's the one we want (not a call)
        if line.strip().startswith('def '):
            in_func = True
            func_lines.append(f"L{i}: {line.rstrip()}")
            continue
    if in_func:
        if line.strip().startswith('def '):
            break
        func_lines.append(f"L{i}: {line.rstrip()[:80]}")

if func_lines:
    for fl in func_lines[:100]:
        print(f"  {fl}")
    if len(func_lines) > 100:
        print(f"  ... 외 {len(func_lines) - 100}줄")
else:
    print("  ❌ manage_position 함수 없음!")

# 2) update_stop_loss 호출 조건
print("\n[2] update_stop_loss 호출 조건")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'update_stop_loss' in line and 'def ' not in line:
        # 앞 15줄 컨텍스트
        start = max(0, i-15)
        print(f"\n  === L{i} 호출 전후 ===")
        for j in range(start, min(i+3, len(lines))):
            marker = ">>>" if j == i-1 else "   "
            print(f"  {marker} L{j+1}: {lines[j].rstrip()[:70]}")

# 3) 실제 while 루프에서 뭘 하는지
print("\n[3] run() 루프 내 실제 동작")
print("-" * 50)

in_run = False
in_while = False
for i, line in enumerate(lines, 1):
    if 'def run(' in line:
        in_run = True
        continue
    if in_run:
        if 'while' in line.lower() and 'self.is_running' in line.lower():
            in_while = True
            print(f"  L{i}: {line.strip()}")
            continue
        if in_while:
            # while 내부 핵심 동작만
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                if any(kw in line.lower() for kw in ['manage', 'sl', 'trailing', 'position', 'price', 'check', 'update']):
                    print(f"  L{i}: {stripped[:70]}")
            if i > 1 and lines[i-1].strip().startswith('def '): # Simple heuristic for end of function
                break
        if in_run and line.strip().startswith('def '):
            break

# 4) 트레일링 조건 체크
print("\n[4] 트레일링 시작 조건")
print("-" * 50)

for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'trail_start' in lower or 'trailing_active' in lower or 'start_trailing' in lower:
        print(f"  L{i}: {line.strip()[:75]}")

# 5) SL 변경 로그 출력 여부
print("\n[5] SL 변경 시 로그 출력")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'log' in line.lower() or 'print' in line.lower():
        if 'sl' in line.lower() or 'stop' in line.lower() or 'trail' in line.lower():
            if 'logging.' in line.lower() or 'print(' in line.lower():
                print(f"  L{i}: {line.strip()[:75]}")

print("\n" + "=" * 70)
print("📋 확인 포인트")
print("-" * 50)
print("""
[실제 동작 확인 필요]
1. manage_position이 정말 매초 호출되나?
2. 호출되더라도 조건 불충족으로 SL 안 바뀌나?
3. 트레일링 시작 조건(수익 >= 리스크 × 0.8) 충족했나?
4. update_stop_loss 호출 시 로그가 찍히나?
5. 거래소 API 실제 호출되나?
""")

print("\n결과 공유해줘")
