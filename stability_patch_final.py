from pathlib import Path
import re

base = Path(r'C:\매매전략')

targets = [
    base / 'core' / 'unified_bot.py',
    base / 'GUI' / 'staru_main.py',
    base / 'exchanges' / 'ws_handler.py',
]

print('=' * 70)
print('🔧 Stability Patch 자동 수정')
print('=' * 70)

for target in targets:
    if not target.exists():
        print(f'❌ {target.name} 없음')
        continue
    
    code = target.read_text(encoding='utf-8', errors='ignore')
    original = code
    
    # 1) bare except: → except Exception as e:
    # re.sub with a function to ensure we don't double up or mess up indentation
    def fix_bare_except(match):
        return 'except Exception as e:'
    
    code = re.sub(r'except\s*:', 'except Exception as e:', code)
    
    # 2) except ...: pass → except ...: logging.debug
    lines = code.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # except 라인 다음이 pass인 경우
        if 'except' in line and ':' in line:
            # Get the variable name if it was just changed to 'e' or was already something
            exc_var = 'e' # default since we just changed bare ones to 'e'
            
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() == 'pass':
                    # pass를 로깅으로 교체
                    indent = len(next_line) - len(next_line.lstrip())
                    new_lines.append(' ' * indent + f'logging.debug(f"Handled exception: {{{exc_var}}}")')
                    i += 2
                    continue
        i += 1
    
    code = '\n'.join(new_lines)
    
    # 3) Special case for unified_bot.py: self.exchange access guards
    if target.name == 'unified_bot.py':
        # Protect common access patterns
        # self.exchange.leverage -> (self.exchange.leverage if self.exchange else 1)
        code = re.sub(r'self\.exchange\.leverage', '(self.exchange.leverage if self.exchange else 1)', code)
        code = re.sub(r'self\.exchange\.capital', '(self.exchange.capital if self.exchange else 0)', code)
        code = re.sub(r'self\.exchange\.symbol', '(self.exchange.symbol if self.exchange else "Unknown")', code)
        code = re.sub(r'self\.exchange\.name', '(self.exchange.name if self.exchange else "Unknown")', code)

    # 변경 확인
    if code != original:
        # 백업
        backup = target.with_suffix('.py.bak_stability')
        backup.write_text(original, encoding='utf-8')
        
        # 저장
        target.write_text(code, encoding='utf-8')
        print(f'✅ {target.name} 수정 완료 (백업: {backup.name})')
    else:
        print(f'⚪ {target.name} 변경 없음')

print('\n' + '=' * 70)
print('검증 명령어:')
print('  py -m py_compile core/unified_bot.py')
print('  py -m py_compile GUI/staru_main.py')
print('  py -m py_compile exchanges/ws_handler.py')
print('=' * 70)
