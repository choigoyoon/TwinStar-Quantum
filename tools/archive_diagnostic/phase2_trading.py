from pathlib import Path
import re

base = Path(__file__).parent

print('=' * 70)
print('📈 Phase 2: 매매 로직 점검')
print('=' * 70)

bot_file = base / 'core' / 'unified_bot.py'
strategy_file = base / 'core' / 'strategy_core.py'

#############################################
# [1] 진입 조건
#############################################
print('\n🟢 [1] 진입 조건')
print('-' * 70)

entry_features = {
    'RSI 필터': r'rsi.*[<>].*\d+|pullback.*rsi',
    'W/M 패턴': r'["\']W["\']|["\']M["\']|pattern.*W|pattern.*M',
    'MTF (Multi-Timeframe)': r'mtf|multi.*time|trend.*tf',
    '진입 유효시간': r'validity|valid.*hour|signal.*expire',
    '슬리피지 체크': r'slippage|slip.*check',
    '레버리지 설정': r'set_leverage|leverage.*=',
}

for feat, pattern in entry_features.items():
    found_files = []
    for f in [bot_file, strategy_file]:
        if f.exists():
            code = f.read_text(encoding='utf-8', errors='ignore')
            if re.search(pattern, code, re.I):
                found_files.append(f.name)
    
    if found_files:
        print(f'  ✅ {feat}: {", ".join(found_files)}')
    else:
        print(f'  ❌ {feat}: 미구현')

#############################################
# [2] 청산 조건
#############################################
print('\n🔴 [2] 청산 조건')
print('-' * 70)

exit_features = {
    'Stop Loss (SL)': r'stop.*loss|sl_price|sl_hit',
    'Take Profit (TP)': r'take.*profit|tp_price|tp_hit',
    'Trailing Stop': r'trailing|trail.*stop|trail.*dist',
    'ATR 기반 SL': r'atr.*sl|sl.*atr|atr_mult',
    '시간 기반 청산': r'time.*exit|max.*hold|expire.*close',
    '수동 청산': r'manual.*close|force.*close',
}

for feat, pattern in exit_features.items():
    found_files = []
    for f in [bot_file, strategy_file]:
        if f.exists():
            code = f.read_text(encoding='utf-8', errors='ignore')
            if re.search(pattern, code, re.I):
                found_files.append(f.name)
    
    if found_files:
        print(f'  ✅ {feat}: {", ".join(found_files)}')
    else:
        print(f'  ❌ {feat}: 미구현')

#############################################
# [3] 복리 로직
#############################################
print('\n💰 [3] 복리 로직')
print('-' * 70)

compound_features = {
    'compound_seed 계산': r'compound.*seed|get_compound_seed',
    'cumulative_pnl 누적': r'cumulative.*pnl|total.*pnl',
    'initial_capital 설정': r'initial.*capital',
    'use_compounding 플래그': r'use.*compound',
    'update_capital 함수': r'update.*capital.*compound',
    'trade_storage 연동': r'trade_storage.*add|add_trade',
}

for feat, pattern in compound_features.items():
    if bot_file.exists():
        code = bot_file.read_text(encoding='utf-8', errors='ignore')
        if re.search(pattern, code, re.I):
            # 라인 번호 찾기
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.I):
                    print(f'  ✅ {feat}: L{i+1}')
                    break
        else:
            print(f'  ❌ {feat}: 미구현')

#############################################
# [4] 레버리지 반영
#############################################
print('\n⚡ [4] 레버리지 반영 (PnL 계산)')
print('-' * 70)

if bot_file.exists():
    code = bot_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    pnl_lines = []
    for i, line in enumerate(lines):
        if 'pnl_pct' in line and '=' in line:
            has_lev = 'leverage' in line.lower()
            mark = '✅' if has_lev else '❌'
            pnl_lines.append(f'  {mark} L{i+1}: {line.strip()[:60]}')
    
    for pl in pnl_lines[:10]:
        print(pl)
    if len(pnl_lines) > 10:
        print(f'  ... 외 {len(pnl_lines)-10}개')

#############################################
# [5] 상태 관리
#############################################
print('\n📦 [5] 상태 관리')
print('-' * 70)

state_features = {
    'save_state': r'def save_state',
    'load_state': r'def load_state|_load_state',
    'position 동기화': r'sync.*position|position.*sync',
    'bt_state 정리': r'bt_state.*position.*=.*None',
    'pending_signals': r'pending.*signal|signal.*queue',
}

for feat, pattern in state_features.items():
    if bot_file.exists():
        code = bot_file.read_text(encoding='utf-8', errors='ignore')
        if re.search(pattern, code, re.I):
            print(f'  ✅ {feat}')
        else:
            print(f'  ❌ {feat}')

print('\n' + '=' * 70)
