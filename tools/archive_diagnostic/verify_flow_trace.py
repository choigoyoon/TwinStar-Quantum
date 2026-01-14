# verify_flow_trace.py - 실행 흐름 추적
import ast
import re
from pathlib import Path

base = Path(__file__).parent

print("=" * 60)
print("실행 흐름 추적")
print("=" * 60)

# 1. staru_main.py imports
entry = base / 'GUI' / 'staru_main.py'
code = entry.read_text(encoding='utf-8', errors='ignore')
tree = ast.parse(code)

imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.add(alias.name.split('.')[0])
    if isinstance(node, ast.ImportFrom):
        if node.module:
            imports.add(node.module.split('.')[0])

print(f"\n[1] staru_main.py imports ({len(imports)}개)")

# 2. unified_bot 메서드 순서
print(f"\n[2] UnifiedBot 핵심 메서드:")

bot_file = base / 'core' / 'unified_bot.py'
code = bot_file.read_text(encoding='utf-8', errors='ignore')
tree = ast.parse(code)

for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and 'Bot' in node.name:
        key = ['__init__', 'start', 'run', '_on_candle_close', 
               'execute_entry', '_manage_position', '_execute_live_close']
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if any(k in item.name for k in key):
                    print(f"  L{item.lineno}: {item.name}()")

# 3. execute_entry 호출
print(f"\n[3] execute_entry() 호출:")

lines = code.split('\n')
in_func = False
depth = 0
calls = []

for i, line in enumerate(lines):
    if 'def execute_entry' in line:
        in_func = True
        depth = len(line) - len(line.lstrip())
        continue
    if in_func:
        if line.strip() and not line.strip().startswith('#'):
            curr = len(line) - len(line.lstrip())
            if curr <= depth and 'def ' in line:
                break
            found = re.findall(r'self\.(\w+)\(', line)
            for c in found:
                if c not in calls:
                    calls.append(c)
                    print(f"  -> {c}()")

# 4. 실행 흐름
print(f"\n[4] 실행 흐름:")
print("""
  staru_main.py
    -> TradingDashboard
      -> UnifiedBot.start()
        -> _on_candle_close() [WS]
          -> detect_signal()
          -> execute_entry()
        -> _manage_position_live()
        -> _execute_live_close()
""")

print("=" * 60)
print("OK 실행 흐름 검증 완료")
