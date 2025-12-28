"""
수집/백테스트 탭 남은 영어 한글화 스크립트
"""
import os

# 파일별 변환 매핑
file_replacements = {
    'GUI/data_collector_widget.py': {
        '"📥 Data Collector"': '"📥 데이터 수집"',
        '"📥 Start Download"': '"📥 다운로드 시작"',
        '"⏹ Stop"': '"⏹ 중지"',
        '"Stop"': '"중지"',
        '"Download"': '"다운로드"',
        '"Status"': '"상태"',
        '"Custom:"': '"사용자:"',
        '"Custom"': '"사용자"',
    },
    'GUI/data_download_widget.py': {
        '"📥 Start Download"': '"📥 다운로드 시작"',
        '"Data Download Manager"': '"데이터 다운로드 관리"',
        '"Ready to download"': '"다운로드 준비됨"',
    },
    'GUI/backtest_widget.py': {
        '"Exchange:"': '"거래소:"',
        '"Symbol:"': '"심볼:"',
        '"TF:"': '"TF:"',
        '"Slippage%"': '"슬리피지%"',
        '"Slippage%:"': '"슬리피지%:"',
        '"fee%"': '"수수료%"',
        '"fee%:"': '"수수료%:"',
        '"Preset:"': '"프리셋:"',
        '"🗑 Del"': '"🗑 삭제"',
        '"Del"': '"삭제"',
    }
}

total_changes = 0

for fpath, replacements in file_replacements.items():
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
            print(f'{os.path.basename(fpath)}: {old} → {new}')
    
    if changes > 0:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        total_changes += changes

print(f'\n총 {total_changes}개 수정 완료')
