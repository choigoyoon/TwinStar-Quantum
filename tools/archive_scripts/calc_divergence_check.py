"""계산식 분기점 전수 체크 & 검증 시스템 생성"""
from pathlib import Path
import re

base = Path(r'C:\매매전략')
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔬 계산식 분기점 전수 체크")
print("=" * 70)

# 핵심 계산식 패턴
calc_patterns = {
    'ATR 계산': r'atr.*=|\.atr|atr_value|atr_mult',
    'RSI 계산': r'rsi.*=|\.rsi|rsi_value|rsi_period',
    'SL 계산': r'sl_price.*=|stop_loss.*=|sl_dist',
    'TP 계산': r'tp_price.*=|take_profit.*=|tp_dist',
    'PnL 계산': r'pnl.*=|profit.*=|loss.*=',
    '포지션 사이즈': r'size.*=|qty.*=|amount.*=|position_size',
    '패턴 감지': r'pattern.*=|find_pattern|detect_pattern|[WM]_pattern',
    'Trailing': r'trail.*=|trailing.*=|trail_dist',
    '진입 조건': r'entry.*condition|can_enter|should_enter|valid.*entry',
    '청산 조건': r'close.*condition|should_close|exit.*condition',
}

results = {'strategy': {}, 'bot': {}}

# strategy_core.py 분석
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    print("\n[strategy_core.py] 계산식 위치")
    print("-" * 50)
    
    for name, pattern in calc_patterns.items():
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                if '=' in line or 'def ' in line:
                    matches.append((i, line.strip()[:60]))
        results['strategy'][name] = matches
        if matches:
            print(f"\n  {name}: {len(matches)}개")
            for ln, txt in matches[:3]:
                print(f"    L{ln}: {txt}")
            if len(matches) > 3:
                print(f"    ... 외 {len(matches) - 3}개")

# unified_bot.py 분석
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    print("\n" + "=" * 70)
    print("[unified_bot.py] 계산식 위치")
    print("-" * 50)
    
    for name, pattern in calc_patterns.items():
        matches = []
        for i, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                if '=' in line or 'def ' in line:
                    matches.append((i, line.strip()[:60]))
        results['bot'][name] = matches
        if matches:
            print(f"\n  {name}: {len(matches)}개")
            for ln, txt in matches[:3]:
                print(f"    L{ln}: {txt}")
            if len(matches) > 3:
                print(f"    ... 외 {len(matches) - 3}개")

# 분기점 비교
print("\n" + "=" * 70)
print("🚨 분기점 경고 (백테스트 vs 실매매 차이)")
print("-" * 50)

for name in calc_patterns.keys():
    s_count = len(results['strategy'].get(name, []))
    b_count = len(results['bot'].get(name, []))
    
    if s_count > 0 and b_count > 0:
        status = "✅" if abs(s_count - b_count) < 3 else "⚠️"
        print(f"  {status} {name}: 백테스트 {s_count}개 / 실매매 {b_count}개")
    elif s_count > 0 and b_count == 0:
        print(f"  ❌ {name}: 백테스트에만 있음 ({s_count}개)")
    elif b_count > 0 and s_count == 0:
        print(f"  ❌ {name}: 실매매에만 있음 ({b_count}개)")

# 자동 검증 스크립트 생성
print("\n" + "=" * 70)
print("📦 자동 검증 스크립트 생성")
print("-" * 50)

verify_script = '''"""빌드 전 계산식 동기화 검증 스크립트"""
from pathlib import Path
import re
import sys

def verify_calc_sync():
    base = Path(r'C:\\매매전략')
    strategy = base / 'core' / 'strategy_core.py'
    bot = base / 'core' / 'unified_bot.py'
    
    errors = []
    warnings = []
    
    if not strategy.exists() or not bot.exists():
        print("❌ 핵심 파일 없음")
        return False
    
    s_code = strategy.read_text(encoding='utf-8')
    b_code = bot.read_text(encoding='utf-8')
    
    # 1) ATR mult 동기화 체크
    s_atr = re.findall(r'atr_mult.*?=.*?([0-9.]+)', s_code)
    b_atr = re.findall(r'atr_mult.*?=.*?([0-9.]+)', b_code)
    if s_atr and b_atr:
        if s_atr[0] != b_atr[0]:
            errors.append(f"ATR mult 불일치: 백테스트={s_atr[0]} vs 실매매={b_atr[0]}")
    
    # 2) RSI 기간 체크
    s_rsi = re.findall(r'rsi_period.*?=.*?([0-9]+)', s_code)
    b_rsi = re.findall(r'rsi_period.*?=.*?([0-9]+)', b_code)
    if s_rsi and b_rsi:
        if s_rsi[0] != b_rsi[0]:
            errors.append(f"RSI period 불일치: 백테스트={s_rsi[0]} vs 실매매={b_rsi[0]}")
    
    # 3) Pullback RSI 체크
    s_pull = re.findall(r'pullback_rsi.*?([0-9]+)', s_code)
    b_pull = re.findall(r'pullback_rsi.*?([0-9]+)', b_code)
    if s_pull and not b_pull:
        warnings.append("Pullback RSI: 실매매에 없음")
    
    # 4) 패턴 tolerance 체크
    s_tol = re.findall(r'pattern_tolerance.*?=.*?([0-9.]+)', s_code)
    b_tol = re.findall(r'pattern_tolerance.*?=.*?([0-9.]+)', b_code)
    if s_tol and b_tol:
        if s_tol[0] != b_tol[0]:
            errors.append(f"Pattern tolerance 불일치: 백테스트={s_tol[0]} vs 실매매={b_tol[0]}")
    
    # 5) Entry validity 체크
    s_val = re.findall(r'entry_validity.*?=.*?([0-9.]+)', s_code)
    b_val = re.findall(r'entry_validity.*?=.*?([0-9.]+)', b_code)
    if s_val and b_val:
        if s_val[0] != b_val[0]:
            warnings.append(f"Entry validity 다름: 백테스트={s_val[0]} vs 실매매={b_val[0]}")
    
    # 결과 출력
    print("=" * 60)
    print("🔍 계산식 동기화 검증 결과")
    print("=" * 60)
    
    if errors:
        print(f"\\n❌ 오류: {len(errors)}개")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print(f"\\n⚠️ 경고: {len(warnings)}개")
        for w in warnings:
            print(f"  - {w}")
    
    if not errors and not warnings:
        print("\\n✅ 모든 계산식 동기화 확인")
    
    print("\\n" + "=" * 60)
    
    if errors:
        print("❌ 빌드 중단 - 오류 수정 필요")
        return False
    else:
        print("✅ 빌드 진행 가능")
        return True

if __name__ == "__main__":
    success = verify_calc_sync()
    sys.exit(0 if success else 1)
'''

verify_path = base / 'verify_calc_sync.py'
verify_path.write_text(verify_script, encoding='utf-8')
print(f"✅ 생성됨: {verify_path}")
print("\n사용법:")
print("  빌드 전: py C:\\매매전략\\verify_calc_sync.py")
print("  통과 시: pyinstaller staru_clean.spec --noconfirm")
