from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('🔍 전체 거래소 float() 위험 패턴 스캔')
print('=' * 70)

issues = []

for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            ln = i + 1
            
            # 패턴 1: float(xxx.get_balance(...))
            if re.search(r'float\s*\(\s*\w+\.get_balance', line):
                issues.append(('float(get_balance)', fname, ln, line.strip()[:60]))
            
            # 패턴 2: float(xxx.fetch_balance(...))
            if re.search(r'float\s*\(\s*\w+\.fetch_balance', line):
                issues.append(('float(fetch_balance)', fname, ln, line.strip()[:60]))
            
            # 패턴 3: float(response) / float(result) / float(data)
            if re.search(r'float\s*\(\s*(response|result|data|ret|res)\s*[\)\[]', line):
                issues.append(('float(response/result)', fname, ln, line.strip()[:60]))
            
            # 패턴 4: float(xxx or 0) where xxx could be dict
            if re.search(r'float\s*\(\s*\w+\.(get|fetch)\w*\([^)]*\)\s*(or|\|)', line):
                issues.append(('float(api_call or 0)', fname, ln, line.strip()[:60]))
            
            # 패턴 5: float(balance) without .get()
            if 'float(balance' in line and '.get(' not in line:
                issues.append(('float(balance) raw', fname, ln, line.strip()[:60]))
                
    except Exception:

                
        pass

# 결과 출력
print(f'\n📊 발견된 위험 패턴: {len(issues)}개\n')

by_file = {}
for typ, fname, ln, code in issues:
    if fname not in by_file:
        by_file[fname] = []
    by_file[fname].append((typ, ln, code))

for fname, items in sorted(by_file.items()):
    print(f'📁 {fname}')
    for typ, ln, code in items:
        print(f'   ❌ L{ln} [{typ}]: {code}')
    print()

print('=' * 70)
print('💡 수정 방법:')
print('   float(xxx.get_balance()) → ')
print('   result = xxx.get_balance()')
print('   float(result.get("free", 0) if isinstance(result, dict) else result or 0)')
print('=' * 70)
