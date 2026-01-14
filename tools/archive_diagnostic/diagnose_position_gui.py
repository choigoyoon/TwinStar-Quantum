from pathlib import Path
import re

base = Path(__file__).parent

print('=' * 70)
print('🔍 GUI-Bot 포지션 동기화 진단')
print('=' * 70)

# Trading Dashboard 확인
dash_file = base / 'GUI' / 'trading_dashboard.py'
if dash_file.exists():
    code = dash_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n📍 포지션 표시 로직:')
    
    patterns = {
        'position 읽기': r'self\.position|bot\.position|get_position',
        'state 파일 읽기': r'state\.json|load_state|read.*state',
        'UI 업데이트': r'update.*position|position.*label|setText.*position',
        'QTimer 연결': r'QTimer|timeout.*connect',
        'refresh 함수': r'def.*refresh|def.*update.*status',
    }
    
    for name, pattern in patterns.items():
        matches = [(i+1, lines[i].strip()[:50]) for i, l in enumerate(lines) if re.search(pattern, l, re.I)]
        if matches:
            print(f'  ✅ {name}: {len(matches)}곳')
            for ln, code in matches[:2]:
                print(f'      L{ln}: {code}')
        else:
            print(f'  ❌ {name}: 없음')
    
    # Active Bot Status 위젯 확인
    print('\n📍 Active Bot Status 위젯:')
    if 'ActiveBotStatus' in code or 'active.*bot' in code.lower():
        print('  ✅ ActiveBotStatus 위젯 존재')
    else:
        print('  ⚠️ ActiveBotStatus 위젯 확인 필요')
    
    # 포지션 상태 업데이트 주기
    print('\n📍 업데이트 주기:')
    timer_matches = re.findall(r'setInterval\((\d+)\)|QTimer.*(\d+)', code)
    if timer_matches:
        for m in timer_matches[:3]:
            interval = m[0] or m[1]
            print(f'  타이머: {interval}ms')

print('\n' + '=' * 70)
