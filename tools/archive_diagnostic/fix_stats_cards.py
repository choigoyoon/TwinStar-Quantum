"""
history_widget.py 통계 카드 한글화 스크립트
"""

# 변환 매핑
replacements = {
    '"Total Trades"': '"총 거래"',
    '"Win Rate"': '"승률"',
    '"Total PnL"': '"총 손익"',
    '"Profit Factor"': '"수익 팩터"',
    '"Avg PnL"': '"평균 손익"',
    '"Max Drawdown"': '"최대 낙폭"',
    '"Best Trade"': '"최고 수익"',
    '"Worst Trade"': '"최대 손실"',
    '"Max Win Streak"': '"최대 연승"',
    '"Max Lose Streak"': '"최대 연패"',
    '"BE Trigger Rate"': '"BE 발동률"',
    '"Current Capital"': '"현재 자본"',
    '"📜 Trade History"': '"📜 거래 내역"',
    '"📂 Import CSV"': '"📂 CSV 가져오기"',
    '"🔄 Refresh"': '"🔄 새로고침"',
    '"📥 Export CSV"': '"📥 CSV 내보내기"',
    '"No trades to display"': '"표시할 거래 없음"',
}

fpath = 'GUI/history_widget.py'

with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0
for old, new in replacements.items():
    if old in content:
        count = content.count(old)
        content = content.replace(old, new)
        changes += count
        print(f'✅ {old} → {new}')

if changes > 0:
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'\n총 {changes}개 수정 완료')
else:
    print('수정할 항목 없음')
