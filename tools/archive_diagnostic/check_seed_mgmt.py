"""시드 관리 기능 확인"""
from pathlib import Path
import os
import json

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'
gui_dir = base / 'GUI'
gui_files = list(gui_dir.glob('*.py')) if gui_dir.exists() else []

print("=" * 70)
print("🔍 시드 관리 기능 확인")
print("=" * 70)

# 1) 시드 설정 UI
print("\n[1] GUI에서 시드 설정")
print("-" * 50)

for gf in gui_files:
    try:
        code = gf.read_text(encoding='utf-8')
        if 'seed' in code.lower() or 'capital' in code.lower() or 'initial' in code.lower():
            for i, line in enumerate(code.split('\n'), 1):
                lower = line.lower()
                if ('seed' in lower or 'capital' in lower) and ('input' in lower or 'edit' in lower or 'spinbox' in lower or 'lineedit' in lower):
                    print(f"  {gf.name} L{i}: {line.strip()[:60]}")
    except:
        pass

# 2) 시드 리셋 기능
print("\n[2] 시드 리셋/초기화 기능")
print("-" * 50)

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    for i, line in enumerate(code.split('\n'), 1):
        lower = line.lower()
        if 'reset' in lower and ('seed' in lower or 'capital' in lower or 'pnl' in lower):
            print(f"  L{i}: {line.strip()[:70]}")

# 3) 시드 추가/차감
print("\n[3] 시드 추가/차감 기능")
print("-" * 50)

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    for i, line in enumerate(code.split('\n'), 1):
        lower = line.lower()
        if ('add' in lower or 'withdraw' in lower or 'deposit' in lower) and ('seed' in lower or 'capital' in lower):
            print(f"  L{i}: {line.strip()[:70]}")

# 4) 프리셋/설정에서 시드
print("\n[4] 프리셋/설정 파일 시드")
print("-" * 50)

for pf in base.glob('**/*.json'):
    if '__pycache__' in str(pf) or '_backup' in str(pf) or 'node_modules' in str(pf):
        continue
    try:
        data = json.loads(pf.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            # Flatten search for deep keys
            def find_keys(d, path=""):
                for k, v in d.items():
                    current_path = f"{path}.{k}" if path else k
                    if any(x in k.lower() for x in ['seed', 'capital', 'initial']):
                        print(f"  {pf.name}: {current_path} = {v}")
                    if isinstance(v, dict):
                        find_keys(v, current_path)
            find_keys(data)
    except:
        pass

# 5) 거래소 잔고 동기화
print("\n[5] 거래소 잔고 동기화")
print("-" * 50)

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    for i, line in enumerate(code.split('\n'), 1):
        if 'get_balance' in line or 'fetch_balance' in line:
            print(f"  L{i}: {line.strip()[:70]}")

print("\n" + "=" * 70)
print("📋 필요한 기능 목록")
print("-" * 50)
print("""
[현재 있는지 확인 필요]
□ 시드 수동 입력 UI
□ 시드 추가 버튼
□ 시드 차감 버튼  
□ 완전 초기화 (PnL 리셋)
□ 거래소 잔고 동기화

[구현 방향]
1. 설정에서 "초기 시드" 입력
2. "시드 조정" 버튼 → +/- 금액 입력
3. "초기화" 버튼 → 누적 PnL 리셋
4. 선택: 거래소 잔고 자동 동기화
""")

print("\n결과 공유해줘")
