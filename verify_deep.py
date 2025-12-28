# verify_deep.py - 심층 검증 (Edge Cases + 숨겨진 문제)
import os
import re

base_path = r'C:\매매전략'

print("=" * 60)
print("심층 검증 (Edge Cases + 숨겨진 문제)")
print("=" * 60)

issues = []

bot_path = os.path.join(base_path, 'core/unified_bot.py')
with open(bot_path, 'r', encoding='utf-8') as f:
    bot_content = f.read()

# [1] Edge Cases
print("\n[1] Edge Cases")
if 'balance' in bot_content.lower() and ('< 10' in bot_content or '<= 0' in bot_content):
    print("  OK 최소 잔고 체크")
else:
    print("  ! 최소 잔고 체크 권장")
    issues.append("! 최소 잔고 체크")

if 'atr' in bot_content.lower() and ('atr <= 0' in bot_content or 'max(atr' in bot_content or 'atr > 0' in bot_content):
    print("  OK ATR 0 방지")
else:
    print("  ! ATR 0 방지 권장")
    issues.append("! ATR 0 방지")

# [2] 타이밍
print("\n[2] 타이밍 문제")
if '_on_candle_close' in bot_content:
    print("  OK 캔들 마감 콜백")
if 'time.sleep' in bot_content or 'sleep' in bot_content:
    print("  OK Rate Limit 처리")
else:
    print("  ! Rate Limit 처리 권장")
    issues.append("! Rate Limit")

# [3] 네트워크
print("\n[3] 네트워크 장애")
ws_path = os.path.join(base_path, 'exchanges/ws_handler.py')
if os.path.exists(ws_path):
    with open(ws_path, 'r', encoding='utf-8') as f:
        ws = f.read()
    if 'reconnect' in ws.lower():
        print("  OK WS 재연결")
    if 'max_reconnect' in ws.lower():
        print("  OK 재연결 제한")

if 'timeout' in bot_content.lower():
    print("  OK 타임아웃 설정")
else:
    print("  ! 타임아웃 권장")
    issues.append("! 타임아웃")

if 'retry' in bot_content.lower():
    print("  OK 재시도 로직")

# [4] 상태 복구
print("\n[4] 상태 복구")
if 'load_state' in bot_content and 'save_state' in bot_content:
    print("  OK 상태 저장/로드")
if '_sync' in bot_content.lower():
    print("  OK 거래소 동기화")
if 'backfill' in bot_content.lower():
    print("  OK 데이터 갭 복구")

# [5] 정밀도
print("\n[5] 계산 정밀도")
rounds = bot_content.count('round(')
print(f"  round() 사용: {rounds}회")
if rounds > 5:
    print("  OK 소수점 처리")

# [6] 예외 처리
print("\n[6] 예외 처리")
excepts = bot_content.count('except')
trys = bot_content.count('try:')
print(f"  try: {trys}회, except: {excepts}회")
if trys > 0 and excepts >= trys:
    print("  OK 예외 처리 균형")

# [7] 메모리
print("\n[7] 메모리 관리")
if 'tail(' in bot_content:
    print("  OK DataFrame tail() 사용")
if 'RotatingFileHandler' in bot_content or 'TimedRotating' in bot_content:
    print("  OK 로그 로테이션")
else:
    print("  ! 로그 로테이션 권장")
    issues.append("! 로그 로테이션")

# [8] 보안
print("\n[8] 보안")
if re.search(r'api_key\s*=\s*["\'][^"\']{20,}["\']', bot_content, re.I):
    print("  X API 키 하드코딩!")
    issues.append("X API 키 하드코딩")
else:
    print("  OK API 키 하드코딩 없음")

# 결과
print("\n" + "=" * 60)
critical = [i for i in issues if i.startswith('X')]
warning = [i for i in issues if i.startswith('!')]

print(f"치명적: {len(critical)}개, 경고: {len(warning)}개")

for c in critical:
    print(f"  {c}")
for w in warning:
    print(f"  {w}")

if len(critical) == 0:
    print("\nOK 치명적 문제 없음 - 빌드 가능")
else:
    print("\nX 수정 필요")
print("=" * 60)
