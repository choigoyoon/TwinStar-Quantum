import sqlite3
import os

DB_PATH = r'C:\매매전략\data\trades.db'

if not os.path.exists(DB_PATH):
    print(f"DB not found: {DB_PATH}")
else:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    # Get recent trades
    cursor.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 20;")
    rows = cursor.fetchall()
    
    print(f"\n=== Recent {len(rows)} Trades ===")
    for row in rows:
        print(row)
    
    # Get summary
    cursor.execute("""
        SELECT COUNT(*), SUM(pnl), SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM trades
    """)
    summary = cursor.fetchone()
    print(f"\nSummary: Total={summary[0]}, Total PnL={summary[1]}, Wins={summary[2]}")
    
    conn.close()
