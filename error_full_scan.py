from pathlib import Path
import re

base = Path(r'C:\매매전략')
all_py = [f for f in base.rglob('*.py') if '__pycache__' not in str(f)]

print('=' * 70)
print('🔴 에러 패턴 전수 스캔 (상세)')
print(f'📁 대상: {len(all_py)}개 .py 파일')
print('=' * 70)

issues = {
    'df_danger': [],
    'signal_get': [],
    'except_pass': [],
    'hardcode_path': [],
    'async_sleep': [],
    'none_check': [],
    'div_zero': [],
    'bare_except': [],
}

for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            ln = i + 1
            stripped = line.strip()
            
            # 1) DataFrame 위험 패턴
            if re.search(r'if\s+\w*df\w*\s+(or|and)', line, re.I):
                if 'is None' not in line and 'is not None' not in line:
                    issues['df_danger'].append((fname, ln, stripped[:60]))
            
            # 2) signal.get() 위험
            if 'signal.get(' in line or "signal['" in line or 'signal["' in line:
                if 'isinstance' not in line and 'getattr' not in line:
                    if '#' not in line.split('signal')[0]:
                        issues['signal_get'].append((fname, ln, stripped[:60]))
            
            # 3) except: pass
            if stripped.startswith('except') and ':' in stripped:
                next_line = lines[i+1].strip() if i+1 < len(lines) else ''
                if next_line == 'pass':
                    issues['except_pass'].append((fname, ln, stripped[:40]))
            
            # 4) bare except (except: 만)
            if stripped == 'except:' or re.match(r'^except\s*:', stripped):
                issues['bare_except'].append((fname, ln, stripped[:40]))
            
            # 5) 하드코딩 경로
            if re.search(r'["\']C:\\\\', line) or re.search(r'["\']C:/', line):
                if '#' not in line.split('C:')[0]:
                    issues['hardcode_path'].append((fname, ln, stripped[:50]))
            
            # 6) async + time.sleep
            if 'time.sleep' in line:
                context = '\n'.join(lines[max(0,i-20):i])
                if 'async def' in context:
                    issues['async_sleep'].append((fname, ln, stripped[:50]))
            
            # 7) None 체크 없는 self.exchange 호출
            if 'self.exchange.' in line and '(' in line:
                ctx = '\n'.join(lines[max(0,i-3):i])
                if 'if self.exchange' not in ctx and 'is None' not in ctx:
                    if 'except' not in ctx and 'try' not in ctx:
                        if 'self.exchange.leverage' in line or 'self.exchange.capital' in line:
                            issues['none_check'].append((fname, ln, stripped[:50]))
            
            # 8) 0으로 나누기 가능성
            if re.search(r'/\s*(entry|price|self\.position\.entry)', line, re.I):
                ctx = '\n'.join(lines[max(0,i-3):i+1])
                if '> 0' not in ctx and '!= 0' not in ctx and 'if' not in ctx:
                    issues['div_zero'].append((fname, ln, stripped[:50]))
                    
    except Exception as e:
        pass

# ═══════════════════════════════════════
# 결과 출력
# ═══════════════════════════════════════

categories = [
    ('df_danger', '🔴 DataFrame 위험 패턴', 'if df or/and 사용'),
    ('signal_get', '🔴 signal.get() 위험', 'dict 아닌 객체 접근'),
    ('div_zero', '🔴 0 나누기 가능성', 'entry/price 체크 없음'),
    ('bare_except', '🟡 bare except:', '모든 예외 무시'),
    ('except_pass', '🟡 except: pass', '에러 무시'),
    ('none_check', '🟡 None 체크 누락', 'self.exchange 접근'),
    ('async_sleep', '🟡 async + time.sleep', '블로킹 호출'),
    ('hardcode_path', '🟡 하드코딩 경로', 'C:\\ 절대경로'),
]

total_critical = 0
total_warning = 0

for key, title, desc in categories:
    items = issues[key]
    count = len(items)
    
    if '🔴' in title:
        total_critical += count
    else:
        total_warning += count
    
    print(f'\n{title} ({desc}): {count}개')
    print('-' * 70)
    
    if items:
        for fname, ln, code in items[:10]:
            print(f'  {fname} L{ln}: {code}')
        if len(items) > 10:
            print(f'  ... 외 {len(items)-10}개')
    else:
        print('  ✅ 없음')

# 최종 요약
print('\n' + '=' * 70)
print('📊 최종 집계')
print('=' * 70)
print(f'  🔴 CRITICAL: {total_critical}개')
print(f'  🟡 WARNING:  {total_warning}개')
print(f'  📁 총 파일:  {len(all_py)}개')
print()

if total_critical > 0:
    print('  ❌ 치명적 에러 발견 - 수정 필요')
else:
    print('  ✅ 치명적 에러 없음')
print('=' * 70)
