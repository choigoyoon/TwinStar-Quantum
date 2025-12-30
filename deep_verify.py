from pathlib import Path
import re

base = Path(r'C:\매매전략')
bot_file = base / 'core' / 'unified_bot.py'

print('=' * 70)
print('🔬 TwinStar Quantum 심화 검증')
print('=' * 70)

if not bot_file.exists():
    print('❌ unified_bot.py 없음')
    exit()

bot_code = bot_file.read_text(encoding='utf-8', errors='ignore')
bot_lines = bot_code.split('\n')

issues = []

#############################################
# [1] 매매 진입 흐름
#############################################
print('\n🔍 [1] 매매 진입 흐름')
print('-' * 70)

entry_funcs = [
    ('run()', r'def run\(self'),
    ('_process_new_candle()', r'def _process_new_candle'),
    ('_check_entry_live()', r'def _check_entry_live'),
    ('execute_entry()', r'def execute_entry'),
]

for name, pattern in entry_funcs:
    found = False
    for i, line in enumerate(bot_lines):
        if re.search(pattern, line):
            print(f'  ✅ {name}: L{i+1}')
            found = True
            break
    if not found:
        print(f'  ❌ {name}: 없음')
        issues.append(f'진입 함수 누락: {name}')

#############################################
# [2] 청산 흐름
#############################################
print('\n🔍 [2] 청산 흐름')
print('-' * 70)

exit_funcs = [
    ('_close_on_sl()', r'def _close_on_sl'),
    ('_execute_live_close()', r'def _execute_live_close'),
    ('trailing stop 로직', r'trailing|trail_dist'),
]

for name, pattern in exit_funcs:
    count = len([l for l in bot_lines if re.search(pattern, l, re.I)])
    if count > 0:
        print(f'  ✅ {name}: {count}곳')
    else:
        print(f'  ❌ {name}: 없음')
        issues.append(f'청산 로직 누락: {name}')

#############################################
# [3] 복리 로직
#############################################
print('\n🔍 [3] 복리 로직')
print('-' * 70)

compound_items = [
    ('_get_compound_seed()', r'def _get_compound_seed'),
    ('initial_capital', r'self\.initial_capital'),
    ('update_capital_for_compounding()', r'update_capital_for_compounding'),
    ('trade_storage 연동', r'trade_storage\.add_trade|self\.trade_storage'),
]

for name, pattern in compound_items:
    count = len([l for l in bot_lines if re.search(pattern, l)])
    if count > 0:
        print(f'  ✅ {name}: {count}곳')
    else:
        print(f'  ⚠️ {name}: 확인 필요')

#############################################
# [4] 레버리지 PnL
#############################################
print('\n🔍 [4] 레버리지 PnL 적용')
print('-' * 70)

pnl_total = 0
pnl_with_lev = 0

for i, line in enumerate(bot_lines):
    if 'pnl_pct' in line and '=' in line and 'pnl_pct==' not in line:
        pnl_total += 1
        if 'leverage' in line.lower():
            pnl_with_lev += 1
        else:
            print(f'  ⚠️ L{i+1}: {line.strip()[:55]}')

print(f'\n  총 {pnl_total}개 중 {pnl_with_lev}개 레버리지 적용 ({pnl_with_lev*100//max(pnl_total,1)}%)')

if pnl_with_lev < pnl_total:
    issues.append(f'레버리지 미적용 PnL: {pnl_total - pnl_with_lev}개')

#############################################
# [5] 상태 관리
#############################################
print('\n🔍 [5] 상태 저장/복구')
print('-' * 70)

state_items = [
    ('save_state()', r'def save_state'),
    ('load_state()', r'def load_state|def _load_state'),
    ('bt_state 정리', r"bt_state\['position'\]\s*=\s*None"),
]

for name, pattern in state_items:
    count = len([l for l in bot_lines if re.search(pattern, l)])
    if count > 0:
        print(f'  ✅ {name}: {count}곳')
    else:
        print(f'  ⚠️ {name}: 확인 필요')

#############################################
# [6] 시그널 관리
#############################################
print('\n🔍 [6] 시그널 큐')
print('-' * 70)

signal_items = [
    ('pending_signals', r'pending_signals'),
    ('signal 만료', r'validity|expire|valid_until'),
    ('signal 실행', r'execute.*signal|_execute_pending'),
]

for name, pattern in signal_items:
    count = len([l for l in bot_lines if re.search(pattern, l, re.I)])
    if count > 0:
        print(f'  ✅ {name}: {count}곳')
    else:
        print(f'  ⚠️ {name}: 확인 필요')

#############################################
# [7] 거래소 API
#############################################
print('\n🔍 [7] 거래소 API 호출')
print('-' * 70)

api_calls = ['place_market_order', 'close_position', 'get_position', 
             'get_balance', 'set_leverage']

for api in api_calls:
    count = len(re.findall(api, bot_code, re.I))
    if count > 0:
        print(f'  ✅ {api}: {count}회')
    else:
        print(f'  ⚠️ {api}: 호출 없음')

#############################################
# [8] 에러 핸들링
#############################################
print('\n🔍 [8] 핵심 함수 에러 핸들링')
print('-' * 70)

critical_funcs = ['execute_entry', '_close_on_sl', 'run', '_process_new_candle']

for func in critical_funcs:
    # 함수 시작 찾기
    start = None
    for i, line in enumerate(bot_lines):
        if f'def {func}(' in line:
            start = i
            break
    
    if start:
        # 함수 내 try-except 확인 (다음 150줄)
        body = '\n'.join(bot_lines[start:start+150])
        has_try = 'try:' in body and 'except' in body
        print(f'  {"✅" if has_try else "⚠️"} {func}: {"try-except 있음" if has_try else "에러 핸들링 부족"}')
    else:
        print(f'  ❌ {func}: 함수 없음')

#############################################
# [9] GUI 연동
#############################################
print('\n🔍 [9] GUI-Core 연동')
print('-' * 70)

gui_path = base / 'GUI'
if gui_path.exists():
    gui_files = list(gui_path.glob('*.py'))
    bot_usage = 0
    for gf in gui_files:
        try:
            code = gf.read_text(encoding='utf-8', errors='ignore')
            if 'UnifiedBot' in code or 'unified_bot' in code:
                bot_usage += 1
                try:
                    print(f'  ✅ {gf.name}: UnifiedBot 사용')
                except UnicodeEncodeError:
                     print(f'  ✅ {gf.name.encode("utf-8", "ignore").decode("utf-8")}: UnifiedBot 사용')
        except:
            pass
    print(f'\n  UnifiedBot 연동 파일: {bot_usage}개')

#############################################
# 최종 요약
#############################################
print('\n' + '=' * 70)
print('📊 심화 검증 요약')
print('=' * 70)

if issues:
    print(f'  ⚠️ 확인 필요: {len(issues)}개')
    for issue in issues:
        print(f'    - {issue}')
else:
    print('  ✅ 모든 항목 정상')

print('=' * 70)
