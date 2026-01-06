from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략\exchanges')

print("전체 거래소 레버리지 에러 처리:")
print("=" * 60)

for f in sorted(base.glob('*_exchange.py')):
    code = f.read_text(encoding='utf-8', errors='ignore')
    
    has_leverage = 'leverage' in code.lower()
    has_110043 = '110043' in code
    has_not_modified = 'not modified' in code.lower() or 'already' in code.lower()
    
    if has_leverage:
        print(f"\n{f.name}:")
        print(f"  레버리지 설정: ✅")
        print(f"  110043 처리: {'✅' if has_110043 else '❌ 없음'}")
        print(f"  이미 설정됨 처리: {'✅' if has_not_modified else '❌ 없음'}")
        
        # 레버리지 함수 찾기
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'def' in line and 'leverage' in line.lower():
                print(f"  함수: L{i+1} {line.strip()[:50]}")
