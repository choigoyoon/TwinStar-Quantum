from pathlib import Path
import re
import json

base = Path(r'C:\매매전략')
gui_dir = base / 'GUI'

report = {
    'summary': {'pass': 0, 'risk': 0, 'syntax_error': 0},
    'issues': []
}

if gui_dir.exists():
    for f in gui_dir.glob('*.py'):
        try:
            code = f.read_text(encoding='utf-8', errors='ignore')
            compile(code, f.name, 'exec')
            
            # except: pass
            p_matches = re.findall(r'except.*:\s*pass\s*$', code, re.MULTILINE)
            if p_matches:
                report['summary']['pass'] += len(p_matches)
                report['issues'].append({'file': f.name, 'type': 'PASS', 'count': len(p_matches)})
                
            # risky access (simplified)
            lines = code.split('\n')
            r_count = 0
            for i, line in enumerate(lines):
                if re.search(r'\.(get|update)\(', line): continue # ignore already safe
                if re.search(r'\[["\']', line): # dictionary/list indexing
                    # For GUI, we care about data from models/states
                    if any(x in line for x in ['state', 'data', 'info', 'result', 'response']):
                         # look for direct access
                         if re.search(r'\[["\']\w+["\']\]', line):
                             r_count += 1
            
            if r_count > 0:
                report['summary']['risk'] += r_count
                report['issues'].append({'file': f.name, 'type': 'RISK', 'count': r_count})
                
        except SyntaxError as e:
            report['summary']['syntax_error'] += 1
            report['issues'].append({'file': f.name, 'type': 'SYNTAX', 'line': e.lineno})

print(json.dumps(report, indent=2))
with open(base / 'gui_quality_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
