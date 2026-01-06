from pathlib import Path
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')

print('=== 문제 라인 확인 ===')
lines = code.split('\n')
for i, line in enumerate(lines):
    if re.search(r'\(self\.exchange\.\w+ if self\.exchange else [^)]+\)\s*=\s*[^=]', line):
        print(f'L{i+1}: {line.strip()[:60]}')

print('\n=== 수정 중 ===')

# 패턴: (self.exchange.ATTR if self.exchange else DEFAULT) = VALUE
pattern = r'^(\s*)\(self\.exchange\.(\w+) if self\.exchange else [^)]+\)\s*=\s*(.+)$'

new_lines = []
fixed = 0
for i, line in enumerate(lines):
    match = re.match(pattern, line)
    if match:
        indent = match.group(1)
        attr = match.group(2)
        value = match.group(3)
        
        # if self.exchange: 형태로 변환
        new_line = f'{indent}if self.exchange:\n{indent}    self.exchange.{attr} = {value}'
        new_lines.append(new_line)
        fixed += 1
        print(f'✅ L{i+1}: self.exchange.{attr} = ...')
    else:
        new_lines.append(line)

print(f'\n총 {fixed}개 수정')

# 저장
new_code = '\n'.join(new_lines)
bot.write_text(new_code, encoding='utf-8')
print('✅ 저장 완료')

# 문법 검증
print('\n=== 문법 검증 ===')
import py_compile
try:
    py_compile.compile(str(bot), doraise=True)
    print('✅ unified_bot.py 문법 오류 없음')
except py_compile.PyCompileError as e:
    print(f'❌ {e}')
