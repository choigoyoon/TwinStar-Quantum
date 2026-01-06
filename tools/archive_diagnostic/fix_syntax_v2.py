from pathlib import Path
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')

print('=== 문제 라인 확인 (할당 및 복합 할당) ===')
lines = code.split('\n')

# 패턴: (self.exchange.ATTR if self.exchange else DEFAULT) [OP]= VALUE
# OP can be =, +=, -=, *=, /=
pattern = r'^(\s*)\(self\.exchange\.(\w+) if self\.exchange else [^)]+\)\s*(\+?=|[-*/]=)\s*(.+)$'

new_lines = []
fixed = 0
for i, line in enumerate(lines):
    match = re.match(pattern, line)
    if match:
        indent = match.group(1)
        attr = match.group(2)
        op = match.group(3)
        value = match.group(4)
        
        # if self.exchange: 형태로 변환
        new_line = f'{indent}if self.exchange:\n{indent}    self.exchange.{attr} {op} {value}'
        new_lines.append(new_line)
        fixed += 1
        print(f'✅ L{i+1}: self.exchange.{attr} {op} ...')
    else:
        new_lines.append(line)

print(f'\n총 {fixed}개 할당문 수정')

code = '\n'.join(new_lines)

# Fix quote collisions again just in case new ones were missed or introduced
code = code.replace('"Unknown"', "'Unknown'")

bot.write_text(code, encoding='utf-8')
print('✅ 저장 완료')

# 문법 검증
import py_compile
try:
    py_compile.compile(str(bot), doraise=True)
    print('✅ unified_bot.py 모든 문법 오류 해결됨')
except py_compile.PyCompileError as e:
    print(f'❌ 아직 문법 오류 남아있음: {e}')
