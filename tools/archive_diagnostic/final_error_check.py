from pathlib import Path
import py_compile
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')

# 1) 문법 검사
print('=== [1] 문법 검사 ===')
try:
    py_compile.compile(str(bot), doraise=True)
    print('✅ 문법 오류 없음')
except py_compile.PyCompileError as e:
    print(f'❌ 문법 오류: {e}')

# 2) 위험 패턴 검사
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print('\n=== [2] DataFrame 위험 패턴 ===')
# if df or df.empty 패턴 (is None 체크 없는 경우)
df_pattern = re.compile(r'if\s+\w+\s+(or|and)\s+\w+\.empty')
for i, line in enumerate(lines):
    if df_pattern.search(line) and 'is None' not in line:
        print(f'❌ L{i+1}: {line.strip()[:100]}')

print('\n=== [3] signal.get() 패턴 ===')
# signal 객체인데 .get()을 쓰는 경우 (getattr 권장)
for i, line in enumerate(lines):
    if 'signal.get(' in line.lower() and 'getattr' not in line:
        # dict인지 객체인지 모를 때 safety check
        print(f'⚠️ L{i+1}: {line.strip()[:100]}')

print('\n=== [4] None 체크 없는 호출 ===')
# self.exchange.leverage 접근 시 self.exchange None 체크 확인
for i, line in enumerate(lines):
    if '.leverage' in line and 'self.exchange.leverage' in line:
        # 이전 5줄에 None 체크 있는지 확인
        context = '\n'.join(lines[max(0,i-5):i])
        if 'is None' not in context and 'if self.exchange' not in context:
            if 'except' not in context:
                print(f'⚠️ L{i+1}: {line.strip()[:100]}')

print('\n=== [5] 완료 ===')
