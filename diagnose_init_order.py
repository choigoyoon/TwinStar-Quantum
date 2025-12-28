from pathlib import Path
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print("UnifiedBot.__init__ 흐름 분석")
print("=" * 60)

# __init__ 찾기
in_init = False
init_start = 0
init_lines = []

for i, line in enumerate(lines):
    if 'def __init__' in line and 'UnifiedBot' in code[max(0,i-100):i]: # Check context roughly
        in_init = True
        init_start = i
    elif 'def __init__' in line:
        # Check if it belongs to UnifiedBot class
        # Simple check: indentation
        if line.startswith('    def __init__'):
            in_init = True
            init_start = i

    if in_init:
        init_lines.append((i+1, line))
        # 다음 메서드 시작하면 종료 (dedented def)
        if line.strip().startswith('def ') and i > init_start + 5:
            # check indent
            if line.startswith('    def '):
                break

print(f"__init__ 시작: L{init_start+1}\n")

# 핵심 초기화 순서 추출
keywords = ['session', 'exchange', 'api', 'kline', 'get_kline', 'connect', 
            'ws', 'websocket', 'parquet', 'load', 'fetch', 'sync', 'cache']

print("초기화 순서 (핵심만):")
print("-" * 60)
order = []
for ln, line in init_lines:
    line_lower = line.lower()
    for kw in keywords:
        if kw in line_lower and ('=' in line or '(' in line):
            order.append((ln, line.strip()[:60]))
            break
    # API 호출 감지
    if 'get_kline' in line or 'fetch' in line.lower() or 'get_position' in line:
        order.append((ln, f"⚠️ API호출: {line.strip()[:50]}"))
    
    # 캐시 초기화 감지 (문제의 원인일 수 있음)
    if 'init_indicator_cache' in line:
        order.append((ln, f"⚠️ 캐시초기화: {line.strip()[:50]}"))


for ln, desc in order[:30]:
    print(f"L{ln}: {desc}")

print("\n" + "-" * 60)
print("문제 패턴 찾기:")

# session None 체크 없이 호출하는 곳
for i, line in enumerate(lines):
    if 'get_kline' in line and i < 1000: # Limit check to earlier lines
        print(f"L{i+1}: {line.strip()}")
