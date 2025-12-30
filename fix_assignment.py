from pathlib import Path

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print('=== 수정 대상 라인 확인 ===')

# 문제 패턴: (self.exchange.xxx if self.exchange else 0) = 
problem_lines = []
for i, line in enumerate(lines):
    if '(self.exchange.' in line and 'if self.exchange else' in line and ') =' in line:
        # 할당문인지 확인 (== 가 아닌 = )
        if ') = ' in line and ') ==' not in line:
            problem_lines.append((i+1, line))
            print(f'L{i+1}: {line.strip()[:70]}')

print(f'\n총 {len(problem_lines)}개 발견')
print('\n=== 수정 시작 ===')

# 수정
new_lines = []
for i, line in enumerate(lines):
    ln = i + 1
    
    # 패턴: (self.exchange.capital if self.exchange else 0) = VALUE
    if '(self.exchange.' in line and 'if self.exchange else' in line and ') = ' in line and ') ==' not in line:
        # 들여쓰기 추출
        indent = len(line) - len(line.lstrip())
        spaces = ' ' * indent
        
        # 속성과 값 추출
        import re
        match = re.search(r'\(self\.exchange\.(\w+) if self\.exchange else [^)]+\) = (.+)$', line)
        if match:
            attr = match.group(1)
            value = match.group(2)
            
            # 올바른 형태로 변환
            new_line = f'{spaces}if self.exchange:\n{spaces}    self.exchange.{attr} = {value}'
            new_lines.append(new_line)
            print(f'✅ L{ln} 수정: self.exchange.{attr} = {value[:30]}...')
            continue
    
    new_lines.append(line)

# 저장
new_code = '\n'.join(new_lines)
bot.write_text(new_code, encoding='utf-8')
print('\n✅ 저장 완료')

# 검증
print('\n=== 문법 검증 ===')
import py_compile
try:
    py_compile.compile(str(bot), doraise=True)
    print('✅ 문법 오류 없음')
except py_compile.PyCompileError as e:
    print(f'❌ 문법 오류: {e}')
