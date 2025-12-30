"""SL 이동 로직 전수 확인"""
from pathlib import Path

base = Path(r'C:\매매전략')
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 SL 이동(상향) 로직 확인")
print("=" * 70)

# 1) strategy_core에서 SL 업데이트 로직
print("\n[1] strategy_core - SL 업데이트 로직")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    sl_update = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        # SL 변경 관련 패턴
        if any(p in lower for p in ['new_sl', 'sl =', 'sl=', 'stop_loss =', 'update.*sl', 'trail.*sl', 'current_sl']):
            sl_update.append(f"  L{i}: {line.strip()[:75]}")
    
    if sl_update:
        print(f"  발견: {len(sl_update)}개")
        for s in sl_update[:20]:
            print(s)
        if len(sl_update) > 20:
            print(f"  ... 외 {len(sl_update) - 20}개")
    else:
        print("  ❌ SL 업데이트 로직 없음!")

# 2) manage_position_realtime 내부 상세
print("\n[2] manage_position_realtime 함수 전체")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    in_func = False
    func_content = []
    for i, line in enumerate(lines, 1):
        if 'def manage_position_realtime' in line:
            in_func = True
        if in_func:
            func_content.append(f"L{i}: {line.rstrip()[:80]}")
            if len(func_content) > 5 and line.strip().startswith('def ') and 'manage_position' not in line:
                break
    
    if func_content:
        for fc in func_content[:50]:
            print(f"  {fc}")
        if len(func_content) > 50:
            print(f"  ... 외 {len(func_content) - 50}줄")
    else:
        print("  ❌ manage_position_realtime 함수 없음!")

# 3) unified_bot에서 SL 변경 로직
print("\n[3] unified_bot - SL 변경 로직")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    sl_changes = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if 'self.sl' in lower or 'self.stop_loss' in lower or 'self.current_sl' in lower:
            if '=' in line:
                sl_changes.append(f"  L{i}: {line.strip()[:70]}")
        if 'position.sl' in lower or 'position.stop' in lower:
            if '=' in line:
                sl_changes.append(f"  L{i}: {line.strip()[:70]}")
    
    if sl_changes:
        print(f"  발견: {len(sl_changes)}개")
        for s in sl_changes[:15]:
            print(s)
    else:
        print("  ⚠️ SL 변경 로직 미발견")

# 4) 거래소 SL 주문 업데이트
print("\n[4] 거래소 SL 주문 업데이트")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    exchange_sl = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if 'modify' in lower or 'amend' in lower or 'update.*order' in lower:
            exchange_sl.append(f"  L{i}: {line.strip()[:70]}")
        if 'set_stop' in lower or 'place.*stop' in lower:
            exchange_sl.append(f"  L{i}: {line.strip()[:70]}")
        # exchange.update_stop_loss 패턴 추가
        if 'exchange.update_stop_loss' in lower:
            exchange_sl.append(f"  L{i}: {line.strip()[:70]}")
    
    if exchange_sl:
        for e in exchange_sl[:10]:
            print(e)
    else:
        print("  ⚠️ 거래소 SL 주문 업데이트 로직 미발견")

# 5) 트레일링 핵심 로직 패턴
print("\n[5] 트레일링 핵심 패턴")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    
    patterns = {
        'new_sl > current_sl': 'new_sl.*>.*current_sl|new_sl.*>.*sl',
        'max(sl, new_sl)': 'max.*sl',
        'sl = new_sl': 'sl\s*=\s*new_sl',
        'extreme - atr': 'extreme.*-.*atr|high.*-.*atr',
    }
    
    import re
    for desc, pattern in patterns.items():
        matches = re.findall(pattern, code, re.IGNORECASE)
        if matches:
            print(f"  ✅ {desc}: {len(matches)}개")
        else:
            print(f"  ❌ {desc}: 없음")

print("\n" + "=" * 70)
print("📋 핵심 질문")
print("-" * 50)
print("""
확인 필요:
1. SL이 실제로 상향 조정되는 코드가 있는가?
2. 새 SL = 최고가 - (ATR × 배수) 계산이 있는가?
3. new_sl > current_sl 일 때만 업데이트하는가?
4. 거래소 SL 주문도 함께 수정되는가?
""")
print("\n결과 공유해줘")
