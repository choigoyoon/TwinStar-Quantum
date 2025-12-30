import sqlite3
from datetime import datetime

conn = sqlite3.connect('trades.db')
cursor = conn.cursor()

print("=" * 80)
print("📊 trades.db 전체 분석")
print("=" * 80)

# Get all trades
cursor.execute("SELECT * FROM trades ORDER BY id DESC")
rows = cursor.fetchall()

cursor.execute("PRAGMA table_info(trades)")
cols = [c[1] for c in cursor.fetchall()]
print(f"\n컬럼: {cols}")
print(f"총 거래: {len(rows)}개\n")

print("-" * 80)
for row in rows:
    print(f"ID: {row[0]}")
    print(f"  심볼: {row[1]}, 거래소: {row[2]}, 방향: {row[3]}")
    print(f"  진입가: ${row[4]:,.2f}, 청산가: ${row[5]:,.2f}")
    print(f"  수량: {row[6]}, PnL: ${row[7]:.2f} ({row[8]:.2f}%)")
    print(f"  진입시간: {row[9]}, 청산시간: {row[10]}")
    print(f"  소스: {row[11]}, 저장시간: {row[12]}")
    print("-" * 40)

# Statistics
if rows:
    total_pnl = sum(r[7] for r in rows if r[7])
    wins = sum(1 for r in rows if r[7] and r[7] > 0)
    losses = sum(1 for r in rows if r[7] and r[7] < 0)
    print(f"\n📈 통계:")
    print(f"  총 PnL: ${total_pnl:.2f}")
    print(f"  승: {wins}, 패: {losses}")
    print(f"  승률: {wins/(wins+losses)*100:.1f}%" if wins+losses > 0 else "  승률: N/A")

conn.close()
