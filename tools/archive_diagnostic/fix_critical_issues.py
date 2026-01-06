
from pathlib import Path
import re
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')
bot_path = base / 'core' / 'unified_bot.py'

print("=" * 60)
print("긴급 패치: 진입 로직 수정")
print("=" * 60)

code = bot_path.read_text(encoding='utf-8')
original = code

# 백업
backup = bot_path.with_suffix('.py.bak2')
backup.write_text(original, encoding='utf-8')
print(f"백업: {backup}")

changes = 0

# 1. pending_signals 최대 크기 제한 (27211개 방지)
print("\n[1] pending_signals 크기 제한 추가")
if 'maxlen' not in code or 'pending_signals' not in code:
    # deque로 변경하거나 크기 제한 추가
    old = "self.pending_signals = []"
    new = "from collections import deque\n        self.pending_signals = deque(maxlen=100)  # 최대 100개 제한"
    if old in code:
        code = code.replace(old, new)
        changes += 1
        print("  ✅ pending_signals에 maxlen=100 추가")
    else:
        # Check if it's already deque or different init
        if "deque(maxlen=" in code:
             print("  ✅ pending_signals 이미 deque로 설정됨 (추정)")
        else:
             print("  ⚠️ 수동 확인 필요 - 'self.pending_signals = []' 찾지 못함")

# 2. DataFrame ambiguous 에러 수정
print("\n[2] DataFrame or 연산 수정")
# s.get('type') or 'default' → s.get('type', 'default')

# 패턴: .get('key') or 'value' → .get('key', 'value')
# This regex is simple and might miss things or be too aggressive, but per user request:
pattern = r"\.get\(['\"](\w+)['\"]\)\s+or\s+['\"](\w+)['\"]"
replacement = r".get('\1', '\2')"

new_code = re.sub(pattern, replacement, code)
if new_code != code:
    print(f"  ✅ .get() or → .get(, default) 변환 적용됨 (매칭 수: {len(re.findall(pattern, code))})")
    code = new_code
    changes += 1
else:
    print("  ℹ️ .get() or 패턴 변환 없음")

# s.get('key') or s.get('key2') → s.get('key', s.get('key2', ''))
pattern2 = r"\.get\(['\"](\w+)['\"]\)\s+or\s+\w+\.get\(['\"](\w+)['\"]\)"
matches = re.findall(pattern2, code)
if matches:
    print(f"  ⚠️ 복합 or 패턴 {len(matches)}개 발견 - 수동 확인 필요")

# 3. 봉 마감 시 실제 진입 호출
print("\n[3] 봉 마감 → execute_entry 연결 확인")
lines = code.split('\n')
in_candle_close = False
has_entry_call = False

for i, line in enumerate(lines):
    if 'def _on_candle_close' in line:
        in_candle_close = True
    if in_candle_close and 'execute_entry' in line:
        has_entry_call = True
        print(f"  L{i+1}: {line.strip()[:60]}")
    if in_candle_close and line.strip().startswith('def ') and '_on_candle_close' not in line:
        # End of function
        in_candle_close = False 
        # Don't break immediately if we want to search entire file for other things, 
        # but user logic intended to scope to _on_candle_close

if not has_entry_call:
    print("  ❌ _on_candle_close에서 execute_entry 호출 없음!")
    print("  → 수동으로 진입 로직 추가 필요")

# 4. pending 신호 처리 로직 확인
print("\n[4] pending 신호 → 진입 흐름")
for i, line in enumerate(lines):
    if 'pending' in line.lower() and ('pop' in line or 'popleft' in line):
        print(f"  L{i+1}: {line.strip()[:60]}")

# 저장
if changes > 0:
    bot_path.write_text(code, encoding='utf-8')
    print(f"\n✅ {changes}개 변경 저장됨")
else:
    print("\n⚠️ 자동 수정 없음 - 수동 패치 필요")

print("\n" + "=" * 60)
print("수동 확인 필요 사항:")
print("  1. _on_candle_close() 끝에서 pending 신호로 execute_entry 호출")
print("  2. pending_signals ↔ bt_state['pending'] 동기화")
print("  3. 신호 유효시간 12시간 체크")
print("=" * 60)
