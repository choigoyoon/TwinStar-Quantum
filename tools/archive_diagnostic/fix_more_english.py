"""
추가 한글화 일괄 변환 스크립트
"""
import os

# 변환 매핑
replacements = {
    # 공통
    '"No data"': 't("backtest.no_data")',
    '"Refresh"': 't("backtest.refresh")',
    '"Download"': 't("data.download")',
    '"Select All"': 't("common.select_all")',
    '"Clear All"': 't("common.clear_all")',
    '"Add"': 't("common.add")',
    '"Import CSV"': 't("history.import_csv")',
    '"Trade History"': 't("dashboard.trade_history")',
    '"Testnet Mode"': 't("settings.testnet")',
    '"Select Symbols"': 't("data.select_symbols")',
}

# 변환 대상 파일
target_files = [
    'GUI/backtest_widget.py',
    'GUI/bot_status_widget.py',
    'GUI/data_collector_widget.py',
    'GUI/history_widget.py',
    'GUI/trading_dashboard.py',
    'GUI/i18n.py',
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
