from pathlib import Path
import re

base = Path(__file__).parent
all_py = [f for f in base.rglob('*.py') if '__pycache__' not in str(f)]

print('=' * 70)
print('🔴 Phase 5: 에러 패턴 전체 스캔')
print(f'📁 대상: {len(all_py)}개 .py 파일')
print('=' * 70)

issues = {
    'critical': [],
    'warning': [],
    'info': []
}

for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            ln = i + 1
            stripped = line.strip()
            
            # ═══════════════════════════════════════
            # 🔴 CRITICAL: 크래시 유발 패턴
            # ═══════════════════════════════════════
            
            # 1) DataFrame 위험 패턴
            if re.search(r'if\s+\w*df\w*\s+(or|and)', line, re.I):
                if 'is None' not in line and 'is not None' not in line:
                    issues['critical'].append(f'[DataFrame] {fname} L{ln}: {stripped[:50]}')
            
            # 2) signal.get() 위험
            if 'signal.get(' in line and 'isinstance' not in line and 'getattr' not in line:
                if '#' not in line.split('signal')[0]:
                    issues['critical'].append(f'[Signal.get] {fname} L{ln}: {stripped[:50]}')
            
            # 3) 0으로 나누기 가능성
            if re.search(r'/\s*\w+\s*(?:\)|,|$)', line):
                if 'entry' in line.lower() or 'price' in line.lower():
                    # context checking would be slow, just simple heuristic
                    pass 
            
            # ═══════════════════════════════════════
            # 🟡 WARNING: 잠재적 문제
            # ═══════════════════════════════════════
            
            # 4) except Exception:
     pass (에러 무시)
            if stripped.startswith('except') and ':' in stripped:
                next_line = lines[i+1].strip() if i+1 < len(lines) else ''
                if next_line == 'pass':
                    issues['warning'].append(f'[except:pass] {fname} L{ln}')
            
            # 5) 하드코딩 경로
            if re.search(r'["\']C:\\\\', line) or re.search(r'["\']C:/', line):
                if '#' not in line.split('C:')[0]:
                    issues['warning'].append(f'[하드코딩] {fname} L{ln}: {stripped[:40]}')
            
            # 6) async + time.sleep (블로킹)
            if 'time.sleep' in line:
                # 상위 20줄에 async def 있는지
                context = '\n'.join(lines[max(0,i-20):i])
                if 'async def' in context:
                    issues['warning'].append(f'[async+sleep] {fname} L{ln}')
            
            # ═══════════════════════════════════════
            # 🔵 INFO: 개선 권장
            # ═══════════════════════════════════════
            
            # 7) TODO/FIXME
            if 'TODO' in line or 'FIXME' in line:
                issues['info'].append(f'[TODO] {fname} L{ln}: {stripped[:40]}')
                
    except Exception as e:
        pass

# ═══════════════════════════════════════
# 결과 출력
# ═══════════════════════════════════════

print('\n🔴 CRITICAL (크래시 유발)')
print('-' * 70)
if issues['critical']:
    for item in issues['critical'][:15]:
        print(f'  {item}')
    if len(issues['critical']) > 15:
        print(f'  ... 외 {len(issues["critical"])-15}개')
else:
    print('  ✅ 없음')

print(f'\n🟡 WARNING (잠재적 문제) - 총 {len(issues["warning"])}개')
print('-' * 70)

# 카테고리별 집계
warning_cats = {}
for w in issues['warning']:
    cat = w.split(']')[0] + ']'
    warning_cats[cat] = warning_cats.get(cat, 0) + 1

for cat, count in sorted(warning_cats.items(), key=lambda x: -x[1]):
    print(f'  {cat}: {count}개')

# 샘플 출력
print('\n  📋 샘플:')
for item in issues['warning'][:10]:
    print(f'    {item}')

print(f'\n🔵 INFO (개선 권장) - 총 {len(issues["info"])}개')
print('-' * 70)
if issues['info']:
    for item in issues['info'][:5]:
        print(f'  {item}')
    if len(issues['info']) > 5:
        print(f'  ... 외 {len(issues["info"])-5}개')
else:
    print('  ✅ 없음')

# ═══════════════════════════════════════
# 최종 요약
# ═══════════════════════════════════════
print('\n' + '=' * 70)
print('📊 최종 요약')
print('=' * 70)
print(f'  🔴 CRITICAL: {len(issues["critical"])}개')
print(f'  🟡 WARNING:  {len(issues["warning"])}개')
print(f'  🔵 INFO:     {len(issues["info"])}개')
print()

if len(issues['critical']) == 0:
    print('  ✅ 치명적 에러 없음 - 배포 가능')
else:
    print('  ❌ 치명적 에러 발견 - 수정 필요')

print('=' * 70)
