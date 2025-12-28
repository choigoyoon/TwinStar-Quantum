from pathlib import Path
import os
from datetime import datetime

ws = Path(r'C:\매매전략\exchanges\ws_handler.py')
try:
    code = ws.read_text(encoding='utf-8', errors='ignore')

    if 'def run_sync' in code:
        print("✅ run_sync 메서드 존재")
        idx = code.find('def run_sync')
        print(code[idx:idx+200])
    else:
        print("❌ run_sync 메서드 없음 - 추가 필요")
        
    # 파일 마지막 수정 시간
    mtime = os.path.getmtime(ws)
    print(f"\n파일 수정 시간: {datetime.fromtimestamp(mtime)}")
except Exception as e:
    print(f"Error checking file: {e}")
