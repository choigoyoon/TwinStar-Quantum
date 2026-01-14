from pathlib import Path
import py_compile
import re

base = Path(__file__).parent

print('=' * 70)
print('🏁 TwinStar Quantum 최종 검증')
print('=' * 70)

# 1) 핵심 파일 문법 검사
print('\n📋 [1] 핵심 파일 문법 검사')
print('-' * 70)

core_files = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'core/multi_sniper.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'exchanges/ws_handler.py',
    'GUI/staru_main.py',
    'GUI/trading_dashboard.py',
]

errors = []
for fpath in core_files:
    f = base / fpath
    if f.exists():
        try:
            py_compile.compile(str(f), doraise=True)
            print(f'  ✅ {fpath}')
        except py_compile.PyCompileError as e:
            print(f'  ❌ {fpath}: {e}')
            errors.append(fpath)
    else:
        print(f'  ⚠️ {fpath}: 없음')

# 2) 치명적 패턴 재확인
print('\n📋 [2] 치명적 패턴 재확인')
print('-' * 70)

bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    
    # 잘못된 할당문 패턴
    bad_assign = re.findall(r'\(self\.exchange\.\w+ if self\.exchange else [^)]+\)\s*=\s*[^=]', code)
    if bad_assign:
        print(f'  ❌ 잘못된 할당문: {len(bad_assign)}개')
        errors.append('할당문 오류')
    else:
        print('  ✅ 할당문 패턴 정상')
    
    # signal.get() 확인 (핵심 파일만)
    signal_issues = len(re.findall(r'signal\.get\(|signal\[', code))
    print(f'  ⚠️ signal 접근: {signal_issues}개 (확인 권장)')

# 3) 최종 결과
print('\n' + '=' * 70)
print('📊 최종 결과')
print('=' * 70)

if not errors:
    print('  ✅ 모든 검증 통과')
    print('  🚀 v1.5.7 빌드 가능')
    print()
    print('  빌드 명령어:')
    print('    cd C:\\매매전략')
    print('    pyinstaller staru_clean.spec --noconfirm')
else:
    print(f'  ❌ 오류 {len(errors)}개 발견')
    for e in errors:
        print(f'    - {e}')

print('=' * 70)
