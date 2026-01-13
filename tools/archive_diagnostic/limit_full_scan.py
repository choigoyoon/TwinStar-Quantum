from pathlib import Path

base = Path(r'C:\매매전략')

print('=== 1000개 제한 로직 전수 검색 ===\n')

targets = []

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.venv' in str(f) or '_backup' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # 1000개 제한 패턴
            if any(p in line for p in ['1000', 'tail(', 'head(', '[-1000', '[:1000', 'iloc[-', 'limit=1000']):
                if 'parquet' in code.lower() or 'candle' in code.lower() or 'kline' in code.lower() or 'ohlcv' in code.lower():
                    targets.append((f.relative_to(base), i+1, line.strip()[:80]))
    except Exception:

        pass

print(f'발견: {len(targets)}건\n')
for path, ln, line in sorted(targets, key=lambda x: (str(x[0]), x[1])):
    print(f'{path} L{ln}:')
    print(f'  {line}\n')
