"""빌드 전 계산식 동기화 검증 스크립트"""
from pathlib import Path
import re
import sys

def verify_calc_sync():
    base = Path(__file__).parent
    strategy = base / 'core' / 'strategy_core.py'
    bot = base / 'core' / 'unified_bot.py'
    
    errors = []
    warnings = []
    
    if not strategy.exists() or not bot.exists():
        print("❌ 핵심 파일 없음")
        return False
    
    s_code = strategy.read_text(encoding='utf-8')
    b_code = bot.read_text(encoding='utf-8')
    
    # 핵심 파라미터 추출 (더 정확한 패턴)
    def extract_param(code, pattern):
        match = re.search(pattern, code)
        return match.group(1) if match else None
    
    # 1) ATR mult 동기화 체크
    s_atr = extract_param(s_code, r"'atr_mult':\s*([0-9.]+)")
    b_atr = extract_param(b_code, r"DEFAULT_ATR_MULT\s*=\s*([0-9.]+)")
    if s_atr and b_atr:
        if s_atr != b_atr:
            errors.append(f"ATR mult 불일치: 백테스트={s_atr} vs 실매매={b_atr}")
        else:
            print(f"✅ ATR mult: {s_atr}")
    
    # 2) RSI 기간 체크
    s_rsi = extract_param(s_code, r"'rsi_period':\s*([0-9]+)")
    b_rsi = extract_param(b_code, r"DEFAULT_RSI_PERIOD\s*=\s*([0-9]+)")
    if s_rsi and b_rsi:
        if s_rsi != b_rsi:
            errors.append(f"RSI period 불일치: 백테스트={s_rsi} vs 실매매={b_rsi}")
        else:
            print(f"✅ RSI period: {s_rsi}")
    
    # 3) Pattern tolerance 체크
    s_tol = extract_param(s_code, r"'pattern_tolerance':\s*([0-9.]+)")
    b_tol = extract_param(b_code, r"DEFAULT_PATTERN_TOLERANCE\s*=\s*([0-9.]+)")
    if s_tol and b_tol:
        if s_tol != b_tol:
            errors.append(f"Pattern tolerance 불일치: 백테스트={s_tol} vs 실매매={b_tol}")
        else:
            print(f"✅ Pattern tolerance: {s_tol}")
    
    # 4) Entry validity 체크
    s_val = extract_param(s_code, r"'entry_validity_hours':\s*([0-9.]+)")
    b_val = extract_param(b_code, r"DEFAULT_ENTRY_VALIDITY_HOURS\s*=\s*([0-9.]+)")
    if s_val and b_val:
        if s_val != b_val:
            errors.append(f"Entry validity 불일치: 백테스트={s_val} vs 실매매={b_val}")
        else:
            print(f"✅ Entry validity: {s_val}h")
    
    # 5) Trail start 체크
    s_trail_s = extract_param(s_code, r"'trail_start_r':\s*([0-9.]+)")
    b_trail_s = extract_param(b_code, r"DEFAULT_TRAIL_START_R\s*=\s*([0-9.]+)")
    if s_trail_s and b_trail_s:
        if s_trail_s != b_trail_s:
            errors.append(f"Trail start 불일치: 백테스트={s_trail_s} vs 실매매={b_trail_s}")
        else:
            print(f"✅ Trail start: {s_trail_s}")
    
    # 6) Trail dist 체크
    s_trail_d = extract_param(s_code, r"'trail_dist_r':\s*([0-9.]+)")
    b_trail_d = extract_param(b_code, r"DEFAULT_TRAIL_DIST_R\s*=\s*([0-9.]+)")
    if s_trail_d and b_trail_d:
        if s_trail_d != b_trail_d:
            errors.append(f"Trail dist 불일치: 백테스트={s_trail_d} vs 실매매={b_trail_d}")
        else:
            print(f"✅ Trail dist: {s_trail_d}")
    
    # 7) Pullback RSI 체크
    s_pull_l = extract_param(s_code, r"'pullback_rsi_long':\s*([0-9]+)")
    b_pull_l = extract_param(b_code, r"DEFAULT_PULLBACK_RSI_LONG\s*=\s*([0-9]+)")
    s_pull_s = extract_param(s_code, r"'pullback_rsi_short':\s*([0-9]+)")
    b_pull_s = extract_param(b_code, r"DEFAULT_PULLBACK_RSI_SHORT\s*=\s*([0-9]+)")
    
    if s_pull_l and b_pull_l and s_pull_l != b_pull_l:
        errors.append(f"Pullback RSI Long 불일치: 백테스트={s_pull_l} vs 실매매={b_pull_l}")
    else:
        print(f"✅ Pullback RSI Long: {s_pull_l or 'N/A'}")
    
    if s_pull_s and b_pull_s and s_pull_s != b_pull_s:
        errors.append(f"Pullback RSI Short 불일치: 백테스트={s_pull_s} vs 실매매={b_pull_s}")
    else:
        print(f"✅ Pullback RSI Short: {s_pull_s or 'N/A'}")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("🔍 계산식 동기화 검증 결과")
    print("=" * 60)
    
    if errors:
        print(f"\n❌ 오류: {len(errors)}개")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print(f"\n⚠️ 경고: {len(warnings)}개")
        for w in warnings:
            print(f"  - {w}")
    
    if not errors and not warnings:
        print("\n✅ 모든 계산식 동기화 확인")
    
    print("\n" + "=" * 60)
    
    if errors:
        print("❌ 빌드 중단 - 오류 수정 필요")
        return False
    else:
        print("✅ 빌드 진행 가능")
        return True

if __name__ == "__main__":
    success = verify_calc_sync()
    sys.exit(0 if success else 1)
