import sqlite3
import os
from pathlib import Path

db_path = Path(r'C:\매매전략\trades.db')

if not db_path.exists():
    print("❌ trades.db not found")
else:
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("⚠️ No tables in trades.db")
        else:
            for table in tables:
                t_name = table[0]
                print(f"\n--- Table: {t_name} (Last 5) ---")
                try:
                    cursor.execute(f"SELECT * FROM {t_name} ORDER BY rowid DESC LIMIT 5;")
                    rows = cursor.fetchall()
                    # 컬럼명 가져오기
                    cursor.execute(f"PRAGMA table_info({t_name});")
                    cols = [c[1] for c in cursor.fetchall()]
                    print(f"Columns: {cols}")
                    for row in rows:
                        print(row)
                except Exception as e:
                    print(f"Error reading table {t_name}: {e}")
        conn.close()
    except Exception as e:
        print(f"DB Connection Error: {e}")
