from pathlib import Path
import re

base = Path(__file__).parent

print('=' * 70)
print('🔍 Stability Patch 수정 대상 정확히 추출')
print('=' * 70)

targets = {
    'core/unified_bot.py': [],
    'GUI/staru_main.py': [],
    'exchanges/ws_handler.py': [],
}

for fpath in targets.keys():
    f = base / fpath
    if not f.exists():
        print(f'❌ {fpath} 없음')
        continue
    
    code = f.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print(f'\n📄 {fpath}')
    print('-' * 70)
    
    issues = []
    
    for i, line in enumerate(lines):
        ln = i + 1
        stripped = line.strip()
        
        # 1) self.exchange 미보호 접근
        if 'self.exchange.' in line:
            attrs = ['leverage', 'capital', 'symbol', 'name']
            for attr in attrs:
                if f'self.exchange.{attr}' in line:
                    # 이전 3줄에 if self.exchange 체크 있는지
                    ctx = '\n'.join(lines[max(0,i-3):i])
                    if 'if self.exchange' not in ctx and 'if not self.exchange' not in ctx:
                        if 'try' not in ctx:
                            issues.append(('🔴 exchange미보호', ln, stripped[:50]))
                            break
        
        # 2) bare except Exception:
        if re.match(r'^\s*except\s*:\s*$', line):
            issues.append(('🟡 bare except', ln, stripped))
        
        # 3) except Exception:
     pass
        if 'except' in line and ':' in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line == 'pass':
                    issues.append(('🟡 except Exception:
     pass', ln, stripped[:30]))
    
    targets[fpath] = issues
    
    if issues:
        for cat, ln, code in issues[:20]:
            print(f'  {cat} L{ln}: {code}')
        if len(issues) > 20:
            print(f'  ... 외 {len(issues)-20}개')
    else:
        print('  ✅ 이슈 없음')

# 요약
print('\n' + '=' * 70)
print('📊 수정 필요 요약')
print('=' * 70)

for fpath, issues in targets.items():
    critical = len([i for i in issues if '🔴' in i[0]])
    warning = len([i for i in issues if '🟡' in i[0]])
    print(f'  {fpath}: 🔴 {critical}개, 🟡 {warning}개')
