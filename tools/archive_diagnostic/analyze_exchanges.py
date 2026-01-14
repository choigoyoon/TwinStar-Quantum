from pathlib import Path
import re

base = Path(__file__).parent
exchanges = base / 'exchanges'

print("=" * 70)
print("전체 거래소 기능 분석")
print("=" * 70)

# 분석할 기능 목록
features = {
    'get_position': ['get_position', 'fetch_position', 'get_positions'],
    'get_balance': ['get_balance', 'fetch_balance', 'balance'],
    'place_order': ['place_order', 'place_market_order', 'create_order'],
    'cancel_order': ['cancel_order', 'cancel_all'],
    'get_history': ['get_trade_history', 'fetch_my_trades', 'get_orders', 'trade_history', 'fetch_orders'],
    'set_leverage': ['set_leverage', 'leverage'],
    'websocket': ['websocket', 'start_websocket', 'ws_connect'],
    'time_sync': ['sync_time', 'fetchTime', 'get_server_time'],
    'position_mode': ['positionIdx', 'positionSide', 'posSide', 'hedge'],
}

results = {}

for f in sorted(exchanges.glob('*_exchange.py')):
    name = f.stem.replace('_exchange', '')
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    lines = len(code.split('\n'))
    
    results[name] = {'lines': lines, 'features': {}}
    
    for feat, keywords in features.items():
        found = any(kw in code for kw in keywords)
        results[name]['features'][feat] = found

# 출력
print("\n[1] 거래소별 기능 매트릭스")
print("-" * 70)

# 헤더
header = f"{'거래소':<12}"
for feat in features.keys():
    header += f"{feat[:8]:<10}"
print(header)
print("-" * 70)

for name, data in sorted(results.items()):
    row = f"{name:<12}"
    for feat in features.keys():
        status = "O" if data['features'][feat] else "X"
        row += f"{status:<10}"
    print(f"{row} ({data['lines']}줄)")

# 상세 분석
print("\n" + "=" * 70)
print("[2] 포지션 조회 상세 분석")
print("-" * 70)

for f in sorted(exchanges.glob('*_exchange.py')):
    name = f.stem.replace('_exchange', '')
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    lines = code.split('\n')
    
    print(f"\n{name}:")
    
    # get_position 함수 찾기
    found_func = False
    for i, line in enumerate(lines):
        if re.search(r'def\s+(get_position|fetch_position|get_positions)', line):
            print(f"  O L{i+1}: {line.strip()[:50]}")
            found_func = True
            # 반환 타입 확인 (다음 15줄)
            for j in range(i+1, min(i+16, len(lines))):
                if 'return' in lines[j]:
                    print(f"      L{j+1}: {lines[j].strip()[:50]}")
                    break
            break
    if not found_func:
        print("  X get_position 없음")

print("\n" + "=" * 70)
print("[3] 거래 내역 조회 상세 분석")
print("-" * 70)

for f in sorted(exchanges.glob('*_exchange.py')):
    name = f.stem.replace('_exchange', '')
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    lines = code.split('\n')
    
    print(f"\n{name}:")
    
    found = False
    for i, line in enumerate(lines):
        if re.search(r'def\s+(get_trade_history|fetch_my_trades|get_orders|fetch_orders)', line):
            print(f"  O L{i+1}: {line.strip()[:50]}")
            found = True
            break
    
    if not found:
        # fetch_my_trades 호출이라도 있는지
        if 'fetch_my_trades' in code or 'fetch_orders' in code:
            print(f"  [!] ccxt 메서드 직접 호출 (래퍼 없음)")
        else:
            print("  X 거래 내역 조회 없음")

print("\n" + "=" * 70)
print("[4] 누락 기능 요약")
print("-" * 70)

critical_missing = []
for name, data in results.items():
    missing = [f for f, v in data['features'].items() if not v]
    if missing:
        # 중요 기능만 필터
        critical = [m for m in missing if m in ['get_position', 'get_balance', 'place_order', 'get_history']]
        if critical:
            critical_missing.append((name, critical))

if critical_missing:
    print("CRITICAL: 핵심 기능 누락:")
    for name, missing in critical_missing:
        print(f"  {name}: {missing}")
else:
    print("O 모든 거래소 핵심 기능 구현됨")

print("\n" + "=" * 70)
