
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 60)
print("4가지 핵심 문제 검증")
print("=" * 60)

issues = []
passed = []

# ============================================
# 1. API 401 에러 - 시간 동기화
# ============================================
print("\n[1] API 401 - 시간 동기화 검증")

# 각 거래소 fetchTime/sync_time 확인
exchanges = ['bybit', 'binance', 'upbit', 'bithumb', 'bingx', 'okx']
for ex in exchanges:
    found = False
    for f in base.rglob(f'*{ex}*.py'):
        if 'exchange' in f.name.lower():
            code = f.read_text(encoding='utf-8', errors='ignore')
            has_fetch = 'fetchTime' in code or 'fetch_time' in code
            has_sync = 'sync_time' in code or 'time_offset' in code
            if has_fetch or has_sync:
                print(f"  ✅ {ex}: 시간동기화 있음")
                passed.append(f"{ex} 시간동기화")
                found = True
            else:
                print(f"  ❌ {ex}: 시간동기화 없음")
                issues.append(f"{ex} fetchTime 없음")
                found = True
            break
    if not found:
        print(f"  ⚠️ {ex}: 파일 없음")

# ============================================
# 2. 실시간 데이터 수집
# ============================================
print("\n[2] 실시간 데이터 수집 검증")

# WS 재연결 로직
ws_files = list(base.rglob('*ws*.py')) + list(base.rglob('*websocket*.py'))
for f in ws_files:
    code = f.read_text(encoding='utf-8', errors='ignore')
    has_reconnect = 'reconnect' in code.lower()
    has_on_error = 'on_error' in code
    has_ping = 'ping' in code.lower()
    print(f"  {f.name}:")
    print(f"    재연결: {'✅' if has_reconnect else '❌'}")
    print(f"    on_error: {'✅' if has_on_error else '❌'}")
    print(f"    ping: {'✅' if has_ping else '❌'}")
    
    if not has_reconnect:
        issues.append(f"{f.name} 재연결 없음")

# 갭 보충 로직
bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    has_gap = 'gap' in code.lower() or 'backfill' in code.lower()
    has_monitor = 'data_monitor' in code.lower()
    print(f"  unified_bot:")
    print(f"    갭 체크: {'✅' if has_gap else '❌'}")
    print(f"    데이터 모니터: {'✅' if has_monitor else '❌'}")
    
    if has_gap:
        passed.append("갭 보충 로직")
    else:
        issues.append("갭 보충 없음")

# ============================================
# 3. 펜딩 신호 누적
# ============================================
print("\n[3] 펜딩 신호 처리 검증")

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    # maxlen 체크
    has_maxlen = 'maxlen' in code and 'pending' in code
    print(f"  maxlen 제한: {'✅' if has_maxlen else '❌'}")
    
    # 중복 체크 로직
    has_dup_check = False
    for i, line in enumerate(lines):
        if 'pending' in line.lower() and ('not in' in line or 'already' in line.lower() or 'exist' in line.lower()):
            has_dup_check = True
            print(f"  중복체크 L{i+1}: {line.strip()[:50]}")
    
    if not has_dup_check:
        # timestamp 비교로 중복 체크하는지
        for i, line in enumerate(lines):
            if 'pending' in line.lower() and 'timestamp' in line.lower():
                has_dup_check = True
                print(f"  타임스탬프 체크 L{i+1}: {line.strip()[:50]}")
    
    print(f"  중복 방지: {'✅' if has_dup_check else '❌'}")
    
    # 처리 후 제거
    has_pop = 'pop' in code and 'pending' in code
    has_clear = 'clear' in code and 'pending' in code
    has_remove = 'remove' in code and 'pending' in code
    print(f"  처리 후 제거: {'✅' if (has_pop or has_clear or has_remove) else '❌'}")
    
    if not has_maxlen:
        issues.append("pending maxlen 없음")
    if not has_dup_check:
        issues.append("pending 중복체크 없음")

# ============================================
# 4. 현물 숏 차단
# ============================================
print("\n[4] 현물 숏 차단 검증")

# strategy_core.py
strategy = base / 'core' / 'strategy_core.py'
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    has_spot_check = 'spot' in code.lower() and 'short' in code.lower()
    print(f"  strategy_core 숏 차단: {'✅' if has_spot_check else '❌'}")
    if not has_spot_check:
        issues.append("strategy_core 현물 숏 차단 없음")

# unified_bot.py
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    has_spot_block = ('upbit' in code.lower() or 'bithumb' in code.lower()) and 'short' in code.lower() and ('block' in code.lower() or 'skip' in code.lower() or 'return' in code)
    print(f"  unified_bot 숏 차단: {'✅' if has_spot_block else '❌'}")
    if not has_spot_block:
        issues.append("unified_bot 현물 숏 차단 없음")

# ============================================
# 결과 요약
# ============================================
print("\n" + "=" * 60)
print("검증 결과")
print("=" * 60)
print(f"✅ 통과: {len(passed)}개")
print(f"❌ 문제: {len(issues)}개")

if issues:
    print("\n🔴 해결 필요:")
    for i in issues:
        print(f"  - {i}")
else:
    print("\n🎉 모든 핵심 문제 검증 통과!")
    print("\n빌드 진행 가능!")
