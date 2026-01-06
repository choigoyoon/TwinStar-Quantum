from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=== float() + dict 에러 위치 찾기 ===')

for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            # float() 호출 찾기
            if 'float(' in line:
                # balance, response, result 관련
                if any(x in line.lower() for x in ['balance', 'response', 'result', 'data']):
                    print(f'{fname} L{i+1}: {line.strip()[:70]}')
            
            # get_balance 함수 반환값
            if 'def get_balance' in line or 'def fetch_balance' in line:
                print(f'\n{fname} L{i+1}: {line.strip()}')
                # 다음 20줄에서 return 찾기
                for j in range(i+1, min(i+20, len(lines))):
                    if 'return' in lines[j]:
                        print(f'  L{j+1}: {lines[j].strip()[:60]}')
                        break
    except:
        pass
