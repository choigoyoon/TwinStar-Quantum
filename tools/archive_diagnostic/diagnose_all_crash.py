from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 70)
print("전체 파일 크래시 유발 패턴 검사")
print("=" * 70)

critical = []

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or 'test' in str(f).lower():
        continue
    
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = str(f.relative_to(base))
        
        for i, line in enumerate(lines):
            prev = '\n'.join(lines[max(0,i-3):i+1])
            
            # 1. order/result/response/position.get() - bool/None 가능
            if re.search(r'(order|result|response|position|trade|ret|res)\.get\(', line):
                if 'isinstance' not in prev and 'is not None' not in prev:
                    if 'dict' not in prev and 'if ' not in lines[max(0,i-1)]:
                        critical.append(('API응답.get()', fname, i+1, line.strip()[:50]))
            
            # 2. signal.get() - Signal 객체
            if re.search(r'signal\.get\(', line, re.I):
                if 'isinstance' not in prev:
                    critical.append(('signal.get()', fname, i+1, line.strip()[:50]))
            
            # 3. self.xxx.method() - xxx가 None 가능
            match = re.search(r'self\.(session|exchange|ws|ws_handler|position|order|client)\.(\w+)\(', line)
            if match:
                var = match.group(1)
                if f'self.{var} is not None' not in prev and f'if self.{var}' not in prev:
                    critical.append((f'self.{var} None', fname, i+1, line.strip()[:50]))
            
            # 4. response['key'] - KeyError
            if re.search(r"(response|result|data)\[['\"]", line):
                if '.get(' not in line:
                    try_block = '\n'.join(lines[max(0,i-5):i])
                    if 'try:' not in try_block:
                        critical.append(('dict[key]', fname, i+1, line.strip()[:50]))
    except Exception:

        pass

# 유형별 정리
print(f"\n총 {len(critical)}개 발견\n")

by_type = {}
for typ, fname, ln, code in critical:
    if typ not in by_type:
        by_type[typ] = []
    by_type[typ].append((fname, ln, code))

for typ, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
    print(f"\n[{typ}] - {len(items)}개")
    print("-" * 50)
    for fname, ln, code in items[:10]:
        print(f"  {fname} L{ln}: {code}")
    if len(items) > 10:
        print(f"  ... 외 {len(items)-10}개")

print("\n" + "=" * 70)
print("우선순위:")
print("  1. signal.get() - 이미 터진 거")
print("  2. self.session None - 터질 가능성 높음")
print("  3. API응답.get() - order/result bool 반환 시 터짐")
print("  4. dict[key] - KeyError")
print("=" * 70)
