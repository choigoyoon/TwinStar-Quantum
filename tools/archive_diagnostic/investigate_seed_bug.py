from pathlib import Path
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print("복리 시드 계산 로직:")
print("=" * 60)

# _get_compound_seed 함수 찾기
for i, line in enumerate(lines):
    if 'def _get_compound_seed' in line:
        print(f"\nL{i+1}: {line.strip()}")
        # 함수 내용 출력
        for j in range(i+1, min(i+35, len(lines))):
            if lines[j].strip().startswith('def '):
                break
            print(f"L{j+1}: {lines[j]}")

print("\n\n누적 손익 및 시드 관련 구문:")
print("=" * 60)

for i, line in enumerate(lines):
    l_lower = line.lower()
    if 'cumulative_pnl' in l_lower or 'self.seed' in l_lower or 'initial_seed' in l_lower:
        if '=' in line or 'return' in line:
            print(f"L{i+1}: {line.strip()[:100]}")

print("\n\n상태 저장/로드 관련 (Save/Load State):")
print("=" * 60)
for i, line in enumerate(lines):
    if 'save_state' in line or 'load_state' in line:
        if 'def ' in line:
             print(f"\nL{i+1}: {line.strip()}")
             for j in range(i+1, min(i+20, len(lines))):
                if lines[j].strip().startswith('def '):
                    break
                print(f"L{j+1}: {lines[j]}")
