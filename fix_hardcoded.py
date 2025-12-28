"""
GUI 하드코딩 영어 텍스트 → t() 일괄 변환 스크립트
"""
import os
import re

# 변환 매핑 (정확한 문자열 → t() 호출)
replacements = {
    # QMessageBox 제목들
    '"Error"': 't("common.error")',
    '"Success"': 't("common.success")',
    '"Warning"': 't("common.warning")',
    '"Failed"': 't("data.failed")',
    
    # 버튼 및 레이블
    '"Apply"': 't("common.apply")',
    '"Close"': 't("common.close")',
    '"Settings"': 't("settings.title")',
    
    # 모드 텍스트
    'mode_text = "Quick"': 'mode_text = t("optimization.quick")',
    'mode_text = "Deep"': 'mode_text = t("optimization.deep")',
    'mode_text = "Standard"': 'mode_text = t("optimization.standard")',
}

# 변환 대상 파일
target_files = [
    'GUI/backtest_widget.py',
    'GUI/cache_manager_widget.py',
    'GUI/data_collector_widget.py',
    'GUI/data_download_widget.py',
    'GUI/developer_mode_widget.py',
    'GUI/history_widget.py',
    'GUI/login.py',
    'GUI/optimization_widget.py',
    'GUI/settings_widget.py',
    'GUI/telegram_settings_widget.py',
]

total_changes = 0

for fpath in target_files:
    if not os.path.exists(fpath):
        continue
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
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
