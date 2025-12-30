import sqlite3
import os
from pathlib import Path

base_path = Path(r'C:\매매전략')
db_path = base_path / 'trades.db'
logs_path = base_path / 'logs'

print("--- Trades Database (Last 10) ---")
if db_path.exists():
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        for table in tables:
            t_name = table[0]
            print(f"\nTable: {t_name}")
            cursor.execute(f"SELECT * FROM {t_name} ORDER BY rowid DESC LIMIT 10;")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
else:
    print("trades.db not found")

print("\n--- Recent Log Search (ENTRY/CLOSE) ---")
log_files = list(logs_path.glob("*.log*"))
# 최신 파일 순으로 정렬
log_files.sort(key=os.path.getmtime, reverse=True)

for log_file in log_files[:5]:
    print(f"\nSearching in: {log_file.name} (Modified: {os.path.getmtime(log_file)})")
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            # 마지막 500줄에서 키워드 검색
            for line in lines[-1000:]:
                lower = line.lower()
                if 'entry' in lower or 'close' in lower or 'order' in lower or 'trading' in lower:
                    if '[status]' not in lower: # STATUS 로그는 너무 많으므로 제외
                        print(line.strip())
    except Exception as e:
        print(f"Log Error {log_file.name}: {e}")
