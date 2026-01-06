from pathlib import Path
import re

base = Path(r'C:\매매전략')

targets = [
    base / 'core' / 'unified_bot.py',
    base / 'GUI' / 'staru_main.py',
    base / 'exchanges' / 'ws_handler.py',
]

print('=' * 70)
print('🔧 Stability Patch 자동 수정 (V2 - Assignment Safety)')
print('=' * 70)

for target in targets:
    if not target.exists():
        print(f'❌ {target.name} 없음')
        continue
    
    code = target.read_text(encoding='utf-8', errors='ignore')
    original = code
    
    # 1) bare except: → except Exception as e:
    code = re.sub(r'except\s*:', 'except Exception as e:', code)
    
    # 2) except ...: pass → except ...: logging.debug
    lines = code.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        if 'except' in line and ':' in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() == 'pass':
                    indent = len(next_line) - len(next_line.lstrip())
                    new_lines.append(' ' * indent + 'logging.debug(f"Handled exception: {e}")')
                    i += 2
                    continue
        i += 1
    
    code = '\n'.join(new_lines)
    
    # 3) Special case for unified_bot.py: self.exchange access guards (READ ONLY)
    if target.name == 'unified_bot.py':
        # Protect common access patterns ONLY when NOT followed by an assignment operator
        def protect_read(match):
            prop = match.group(1)
            # Check if this is an assignment target
            line_full = match.string
            start, end = match.span()
            # Look ahead for '=' but not '=='
            after = line_full[end:].strip()
            if after.startswith('=') and not after.startswith('=='):
                # This is an assignment, don't wrap it
                return f'self.exchange.{prop}'
            
            # Default values for properties
            defaults = {'leverage': '1', 'capital': '0', 'symbol': '"Unknown"', 'name': '"Unknown"'}
            return f'(self.exchange.{prop} if self.exchange else {defaults.get(prop, "None")})'

        code = re.sub(r'self\.exchange\.(leverage|capital|symbol|name)', protect_read, code)

    # 변경 확인
    if code != original:
        target.write_text(code, encoding='utf-8')
        print(f'✅ {target.name} 수정 완료')
    else:
        print(f'⚪ {target.name} 변경 없음')

print('\n' + '=' * 70)
