from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 60)
print("전체 DataFrame 위험 패턴 스캔")
print("=" * 60)

issues = []

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or 'diagnose' in str(f).lower():
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = str(f.relative_to(base))
        
        for i, line in enumerate(lines):
            # 1. df or / df and 패턴
            if re.search(r'\bdf\w*\s+(or|and)\s+', line):
                if 'is None' not in line and 'isinstance' not in line:
                    issues.append((fname, i+1, 'df or/and', line.strip()[:50]))
            
            # 2. or df / and df 패턴
            if re.search(r'\s+(or|and)\s+\w*df', line, re.I):
                if 'is None' not in line:
                    issues.append((fname, i+1, 'or/and df', line.strip()[:50]))
            
            # 3. if df: 패턴
            if re.search(r'if\s+df\w*\s*:', line):
                issues.append((fname, i+1, 'if df:', line.strip()[:50]))
            
            # 4. not df 패턴
            if re.search(r'not\s+df\w*\s', line):
                if 'is not None' not in line:
                    issues.append((fname, i+1, 'not df', line.strip()[:50]))
            
            # 5. getattr(...) or self.df 패턴 (방금 고친 것)
            if re.search(r'getattr\([^)]+\)\s+or\s+self\.df', line):
                issues.append((fname, i+1, 'getattr or df', line.strip()[:50]))

    except Exception:


        pass

print(f"\n총 {len(issues)}개 발견\n")

for fname, ln, typ, code in issues:
    print(f"{fname} L{ln} [{typ}]: {code}")
