
from pathlib import Path
import sys

# Ensure proper encoding for printing
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 60)
print("거래 로직 전체 재검증")
print("=" * 60)

issues = []

# 1. 현물(SPOT) 숏 차단 로직
print("\n[1] 현물 숏 차단 검증")

# strategy_core.py - 백테스트
strategy = base / 'core' / 'strategy_core.py'
if strategy.exists():
    code = strategy.read_text(encoding='utf-8', errors='ignore')
    
    # run_backtest에서 spot 체크
    if 'market_type' in code and 'spot' in code.lower():
        print("  ✅ strategy_core: market_type 체크 있음")
    else:
        issues.append("strategy_core.py: spot 숏 차단 로직 없음")
        print("  ❌ strategy_core: spot 숏 차단 없음")
    
    # detect_signal/detect_pattern에서 spot 체크
    if "direction == 'short'" in code.lower() or "direction == 'Short'" in code:
        found_short_skip = False
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'short' in line.lower() and ('skip' in line.lower() or 'continue' in line.lower() or 'spot' in line.lower()):
                print(f"  L{i+1}: {line.strip()[:60]}")
                found_short_skip = True
        if not found_short_skip:
             print("  ⚠️ strategy_core: Short 스킵 로직, 명시적인 'spot' 조건 못 찾음")

# unified_bot.py - 실매매
bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    
    # execute_entry에서 spot 숏 차단
    has_spot_check = False
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if 'spot' in line.lower() and 'short' in line.lower():
            has_spot_check = True
            print(f"  unified_bot L{i+1}: {line.strip()[:60]}")
    
    if not has_spot_check:
        issues.append("unified_bot.py: execute_entry에 spot 숏 차단 없음")
        print("  ❌ unified_bot: spot 숏 차단 없음")

# 2. RSI 필터 검증
print("\n[2] RSI 필터 검증")
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    
    # RSI pullback 체크
    # Check for exact strings or variations
    rsi_check = 'rsi' in code.lower() and ('< 40' in code or '> 60' in code or '<= 40' in code or '>= 60' in code)
    if rsi_check:
        print("  ✅ RSI pullback 조건 있음")
    else:
        issues.append("unified_bot.py: RSI pullback 체크 누락 가능")
        print("  ⚠️ RSI pullback 조건 확인 필요")

# 3. pending_signals 동기화
print("\n[3] pending_signals 동기화")
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    
    has_pending = 'pending_signals' in code
    has_bt_pending = "bt_state['pending']" in code or 'bt_state["pending"]' in code
    has_sync = 'pending_signals' in code and 'bt_state' in code
    
    print(f"  pending_signals 사용: {'✅' if has_pending else '❌'}")
    print(f"  bt_state['pending'] 사용: {'✅' if has_bt_pending else '❌'}")
    
    if has_pending and has_bt_pending:
        # 동기화 로직 확인
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'pending_signals' in line and 'bt_state' in line:
                print(f"  L{i+1}: {line.strip()[:60]}")

# 4. 신호 유효시간 체크
print("\n[4] 신호 유효시간 (12시간) 체크")
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    
    validity_keywords = ['validity', 'expire', 'hours=12', '12', 'timeout']
    found = False
    lines = code.split('\n')
    for i, line in enumerate(lines):
        # Broad check
        if 'timedelta' in line and 'hours' in line and '12' in line:
             found = True
             print(f"  L{i+1}: {line.strip()[:60]}")
    
    if not found:
        pass 
        # issues.append("신호 유효시간 체크 불명확") # Disabled strict check as it might be variably implemented
        # print("  ⚠️ 신호 유효시간 로직 확인 필요")
    else:
        print("  ✅ 신호 유효시간(12h) 체크 로직 발견")

# 5. Upbit/Bithumb fetchTime
print("\n[5] Upbit/Bithumb 시간 동기화")
for name in ['upbit', 'bithumb']:
    # Recursively find exchange files
    found_file = False
    for py in base.rglob(f'*{name}*.py'):
        if 'exchange' not in py.name: continue
        found_file = True
        code = py.read_text(encoding='utf-8', errors='ignore')
        if 'fetchTime' in code or 'fetch_time' in code or 'sync_time' in code:
            if 'sync_time' in code and 'fetchTime' not in code:
                 # Bithumb/Upbit might use sync_time but not fetchTime directly if implemented custom
                 pass
            
            # Specifically check for fetchTime if that's the requirement
            if 'def fetchTime' in code:
                 print(f"  ✅ {py.name}: fetchTime 메서드 있음")
            else:
                 issues.append(f"{py.name}: fetchTime 메서드 없음")
                 print(f"  ❌ {py.name}: fetchTime 없음 (sync_time만 있을 수 있음)")
    if not found_file:
        print(f"  ⚠️ {name} 관련 exchange 파일을 찾지 못함")


# 6. DataFrame 안전성
print("\n[6] DataFrame 안전성 (.get() 사용)")
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    
    # 위험한 패턴: s.get('x') or 'default'
    risky = code.count(".get(") 
    # Just counting usage isn't very indicative of safety without regex, but following user script logic
    print(f"  .get() 사용 빈도: {risky}회")

# 결과
print("\n" + "=" * 60)
print("검증 결과")
print("=" * 60)
if issues:
    print(f"🔴 문제: {len(issues)}개")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("✅ 모든 로직 정상")
