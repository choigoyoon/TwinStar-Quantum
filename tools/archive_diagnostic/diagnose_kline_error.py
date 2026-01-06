from pathlib import Path

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print("get_kline 호출 위치:")
print("=" * 50)
for i, line in enumerate(lines):
    if 'get_kline' in line:
        print(f"L{i+1}: {line.strip()[:70]}")

print("\n\nSession 초기화 순서 확인:")
for i, line in enumerate(lines):
    if 'Session not initialized' in line or 'session' in line.lower() and '=' in line:
        print(f"L{i+1}: {line.strip()[:70]}")
