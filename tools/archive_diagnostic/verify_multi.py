"""
멀티 트레이더/스나이퍼 기능 검증 스크립트
"""
import os
import sys
sys.path.insert(0, r'C:\매매전략')

print("=" * 60)
print("🔍 멀티 트레이더/스나이퍼 기능 검증")
print("=" * 60)

# 1. 모듈 Import 테스트
print("\n📊 [1] 모듈 Import 테스트")
print("-" * 40)

try:
    from core.multi_trader import MultiTrader, CoinStatus, CoinState
    print("✅ core.multi_trader 정상")
except Exception as e:
    print(f"❌ core.multi_trader: {e}")

try:
    from core.multi_sniper import MultiCoinSniper
    print("✅ core.multi_sniper 정상")
except Exception as e:
    print(f"❌ core.multi_sniper: {e}")

# 2. GUI 컴포넌트 확인
print("\n📊 [2] GUI 컴포넌트 확인")
print("-" * 40)

gui_files = [
    'GUI/multi_session_popup.py',
    'GUI/sniper_session_popup.py'
]

for f in gui_files:
    if os.path.exists(f):
        print(f"✅ {f}")
    else:
        print(f"❌ {f} 없음")

# 3. 핵심 메서드 확인
print("\n📊 [3] MultiTrader 핵심 메서드")
print("-" * 40)

with open('core/multi_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

methods = [
    'def initialize',
    'def start_websocket',
    'def rotate_subscriptions',
    '_load_all_optimized_coins',
    '_on_bybit_kline',
    '_try_entry',
    '_execute_order',
    '_manage_position'
]

for m in methods:
    status = "✅" if m in content else "❌"
    print(f"{status} {m}")

# 4. MultiSniper 핵심 메서드
print("\n📊 [4] MultiSniper 핵심 메서드")
print("-" * 40)

with open('core/multi_sniper.py', 'r', encoding='utf-8') as f:
    content2 = f.read()

methods2 = [
    'def initialize',
    '_get_top50_by_volume',
    '_calc_readiness',
    '_analyze_pattern',
    '_try_entry',
    '_execute_order',
    '_check_exit_condition',
    '_execute_exit'
]

for m in methods2:
    status = "✅" if m in content2 else "❌"
    print(f"{status} {m}")

# 5. 거래소 연동 확인
print("\n📊 [5] 거래소 연동 확인")
print("-" * 40)

exchanges = ['bybit', 'binance', 'okx', 'bitget']
for ex in exchanges:
    if ex in content.lower() or ex in content2.lower():
        print(f"✅ {ex} 연동 코드 있음")
    else:
        print(f"⚠️ {ex} 연동 코드 없음")

# 6. 웹소켓 연동 확인
print("\n📊 [6] 웹소켓 연동 확인")
print("-" * 40)

ws_patterns = ['_start_bybit_ws', '_start_binance_ws', '_subscribe_ws', 'websocket']
for p in ws_patterns:
    if p in content:
        print(f"✅ {p} 있음")
    else:
        print(f"⚠️ {p} 없음")

# 7. 최적화 JSON 로드 확인
print("\n📊 [7] 최적화 파일 로드")
print("-" * 40)

if 'config/presets' in content or 'optimized' in content.lower():
    print("✅ 최적화 파일 로드 로직 있음")
else:
    print("⚠️ 최적화 파일 로드 확인 필요")

# 8. 알림 시스템 확인
print("\n📊 [8] 알림 시스템")
print("-" * 40)

if '_notify' in content and 'telegram' in content.lower():
    print("✅ 텔레그램 알림 통합")
else:
    print("⚠️ 알림 통합 확인 필요")

# 9. 잠재적 문제 확인
print("\n📊 [9] 잠재적 문제 확인")
print("-" * 40)

issues = []

if 'NotImplemented' in content or 'pass  # TODO' in content:
    issues.append("미구현 코드(TODO/NotImplemented) 발견")

if 'exchange_client' not in content:
    issues.append("exchange_client 연결 누락 가능")

if 'dry_run' not in content:
    issues.append("dry_run 모드 미지원")

if issues:
    for issue in issues:
        print(f"⚠️ {issue}")
else:
    print("✅ 명확한 문제 없음")

# 결론
print("\n" + "=" * 60)
print("📋 검증 결론")
print("=" * 60)
