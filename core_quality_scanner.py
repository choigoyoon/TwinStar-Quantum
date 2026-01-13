from pathlib import Path
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

# 1단계: core/ 폴더만 정밀 스캔
print("=" * 70)
print("1단계: core/ 폴더 정밀 스캔")
print("=" * 70)

core_issues = {
    'except_pass': [],
    'hardcoded': [],
    'unsafe_access': [],
}

for f in (base / 'core').glob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.name
        
        for i, line in enumerate(lines):
            # except Exception:
     pass 또는 except ...: pass
            if re.search(r'except.*:\s*pass', line):
                core_issues['except_pass'].append((fname, i+1, line.strip()[:60]))
            elif re.search(r'except.*:\s*$', line) and i+1 < len(lines) and 'pass' in lines[i+1]:
                 core_issues['except_pass'].append((fname, i+1, line.strip()[:60]))

            # 하드코딩 경로
            if re.search(r'["\']C:[/\\]', line) and '#' not in line.split('C:')[0]:
                core_issues['hardcoded'].append((fname, i+1, line.strip()[:60]))
            
            # result[...], response[...] 직접 접근
            if re.search(r'(result|response|order|data|pos)\[["\']', line):
                if '.get(' not in line:
                    # Check if it's within a try block (heuristic: last 3 lines)
                    surrounding = '\n'.join(lines[max(0,i-3):i+1])
                    if 'try' not in surrounding:
                        core_issues['unsafe_access'].append((fname, i+1, line.strip()[:60]))
    except Exception as e:
        print(f"Error reading {f}: {e}")

print(f"\n[core/] except Exception:
     pass — {len(core_issues['except_pass'])}개")
for fname, ln, code in core_issues['except_pass']:
    print(f"  {fname} L{ln}: {code}")

print(f"\n[core/] 하드코딩 — {len(core_issues['hardcoded'])}개")
for fname, ln, code in core_issues['hardcoded']:
    print(f"  {fname} L{ln}: {code}")

print(f"\n[core/] 위험 접근 — {len(core_issues['unsafe_access'])}개")
for fname, ln, code in core_issues['unsafe_access'][:20]: # Show first 20 for brevity
    print(f"  {fname} L{ln}: {code}")

print("\n→ 완료")
