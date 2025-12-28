from pathlib import Path
import re
import json

base = Path(r'C:\매매전략')
issues = {'except_pass': [], 'hardcoded': [], 'unsafe': []}

for f in (base / 'core').glob('*.py'):
    code = f.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    for i, l in enumerate(lines):
        # 1. except: pass
        if re.search(r'except.*:\s*pass', l) or (re.search(r'except.*:\s*$', l) and i+1 < len(lines) and 'pass' in lines[i+1]):
            issues['except_pass'].append({'file': f.name, 'line': i+1, 'code': l.strip()})
        
        # 2. Hardcoded
        if re.search(r'["\']C:[/\\]', l) and '#' not in l.split('C:')[0]:
            issues['hardcoded'].append({'file': f.name, 'line': i+1, 'code': l.strip()})
            
        # 3. Unsafe
        if re.search(r'(result|response|order|ret|data|pos)\[["\']', l) and '.get(' not in l:
            surrounding = '\n'.join(lines[max(0,i-3):i+1])
            if 'try' not in surrounding:
                issues['unsafe'].append({'file': f.name, 'line': i+1, 'code': l.strip()})

with open(r'C:\매매전략\core_quality_report.json', 'w', encoding='utf-8') as f:
    json.dump(issues, f, ensure_ascii=False, indent=2)
