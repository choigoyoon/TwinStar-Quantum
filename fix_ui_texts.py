"""
추가 UI 한글화 스크립트 - 주요 텍스트만
"""
import os

# 변환 매핑 (UI에 표시되는 텍스트만)
replacements = {
    # trading_dashboard.py
    '"Single Trading"': '"단일 매매"',
    '"Multi Explorer"': '"멀티 탐색기"',
    '"Multi Explorer (Admin Only)"': '"멀티 탐색기 (관리자 전용)"',
    '"Admin Only"': '"(관리자 전용)"',
    
    # telegram_settings_widget.py
    '"Telegram Notifications"': '"텔레그램 알림"',
    '"Bot Token"': '"봇 토큰"',
    '"Chat ID"': '"채팅 ID"',
    
    # optimization_widget.py
    '"Quantum Optimization Engine"': '"퀀텀 최적화 엔진"',
    '"Data Source"': 't("optimization.data_source")',
    '"Manual Settings (Advanced)"': '"고급 설정"',
    '"Optimization Results"': '"최적화 결과"',
    
    # history_widget.py
    '"📋 Table"': '"📋 테이블"',
    '"📈 Equity"': '"📈 자산곡선"',
    '"Table"': '"테이블"',
    '"Equity"': '"자산곡선"',
}

# 변환 대상 파일
target_files = [
    'GUI/trading_dashboard.py',
    'GUI/telegram_settings_widget.py',
    'GUI/optimization_widget.py',
    'GUI/history_widget.py',
    'GUI/settings_widget.py',
]

total_changes = 0

for fpath in target_files:
    if not os.path.exists(fpath):
        continue
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes = 0
    
    for old, new in replacements.items():
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            changes += count
    
    if changes > 0:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✅ {fpath}: {changes}개 수정')
        total_changes += changes

print(f'\n총 {total_changes}개 수정 완료')
