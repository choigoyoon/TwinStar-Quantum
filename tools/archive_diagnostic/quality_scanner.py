from pathlib import Path
import re
import sys
import json

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

issues = {
    'except_pass': [],
    'hardcoded_path': [],
    'unsafe_get': [],
}

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.agent' in str(f) or '.gemini' in str(f):
        continue
    if f.name in ['scanner.py', 'quality_scanner.py', 'diagnose_import.py', 'verify_v144_deploy.py', 'final_integration_test.py']:
        continue
    
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = str(f.relative_to(base))
        
        for i, line in enumerate(lines):
            # 1. except Exception:
     pass
            if 'except' in line and (('pass' in line) or (re.search(r'except\s*:\s*$', line) and i+1 < len(lines) and 'pass' in lines[i+1])):
                issues['except_pass'].append(f"{fname} L{i+1}: {line.strip()}")
            
            # 2. 하드코딩 경로
            if re.search(r'["\']C:[/\\]', line) and '#' not in line.split('C:')[0]:
                issues['hardcoded_path'].append(f"{fname} L{i+1}: {line.strip()}")
            
            # 3. 위험한 .get()
            if re.search(r'(result|response|order|ret|data|pos)\[', line) and '.get(' not in line:
                surrounding = '\n'.join(lines[max(0,i-3):i+1])
                if 'try' not in surrounding:
                    issues['unsafe_get'].append(f"{fname} L{i+1}: {line.strip()}")
    except Exception:

        pass

with open(r'C:\매매전략\quality_report.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("TwinStar Quantum Code Quality Report (v1.4.4 Audit)\n")
    f.write("=" * 70 + "\n\n")
    
    f.write(f"[1] except Exception:
     pass — {len(issues['except_pass'])} issues\n")
    f.write(f"[2] Hardcoded Paths — {len(issues['hardcoded_path'])} issues\n")
    f.write(f"[3] Unsafe Direct Access — {len(issues['unsafe_get'])} issues\n\n")
    
    f.write("-" * 50 + "\n")
    f.write("SAMPLES (10 per category)\n")
    f.write("-" * 50 + "\n\n")
    
    for cat in ['except_pass', 'hardcoded_path', 'unsafe_get']:
        f.write(f"### {cat.upper()} ###\n")
        for x in issues[cat][:10]:
            f.write(f"  {x}\n")
        f.write("\n")

    f.write("-" * 50 + "\n")
    f.write("FULL LISTING\n")
    f.write("-" * 50 + "\n\n")
    for cat in ['except_pass', 'hardcoded_path', 'unsafe_get']:
        f.write(f"### {cat.upper()} ###\n")
        for x in issues[cat]:
            f.write(f"  {x}\n")
        f.write("\n")

print("Report saved to C:\\매매전략\\quality_report.txt")
print(f"Summary: Pass={len(issues['except_pass'])}, Path={len(issues['hardcoded_path'])}, Unsafe={len(issues['unsafe_get'])}")
