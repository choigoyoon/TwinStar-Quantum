"""
GUI 파일에 t() 임포트 추가 스크립트
"""
import os

files_to_fix = [
    'GUI/backtest_widget.py',
    'GUI/cache_manager_widget.py',
    'GUI/data_collector_widget.py',
    'GUI/data_download_widget.py',
    'GUI/developer_mode_widget.py',
    'GUI/history_widget.py',
    'GUI/login.py',
    'GUI/telegram_settings_widget.py',
]

import_line = "from locales.lang_manager import t\n"

for fpath in files_to_fix:
    if not os.path.exists(fpath):
        print(f"❌ {fpath} 없음")
        continue
    
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 이미 있는지 체크
    if 'from locales.lang_manager import t' in content:
        print(f"✅ {fpath} 이미 있음")
        continue
    
    # 첫 번째 import 문 찾기
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i
            break
    
    # import 문 삽입
    lines.insert(insert_idx, "from locales.lang_manager import t")
    
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ {fpath} 추가 완료")

print("\n모든 파일 수정 완료!")
