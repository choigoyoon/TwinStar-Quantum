from pathlib import Path
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략\exchanges')

print("거래소별 현물/선물 + Position Mode 점검:")
print("=" * 60)

for f in base.glob('*_exchange.py'):
    code = f.read_text(encoding='utf-8', errors='ignore')
    name = f.stem
    
    # 현물/선물 구분
    # category가 있으면 보통 통합(Unified) 또는 선물 API
    is_spot = 'spot' in code.lower() and 'category' not in code.lower()
    # futures/swap/linear/category 키워드로 선물 여부 추정
    is_futures = 'linear' in code.lower() or 'swap' in code.lower() or 'futures' in code.lower() or 'category' in code.lower()
    
    # Position 관련
    has_idx = 'positionIdx' in code or 'position_idx' in code
    has_side = 'positionSide' in code or 'position_side' in code
    
    print(f"\n{name}:")
    # 단순 추정 로직이므로 "불명"일 수 있음
    type_str = '현물' if is_spot and not is_futures else '선물' if is_futures else '불명/기타'
    
    # 예외: upbit/bithumb은 명확히 현물
    if 'upbit' in name or 'bithumb' in name:
        type_str = '현물'
    
    print(f"  타입: {type_str}")
    print(f"  positionIdx: {'✅' if has_idx else '❌'}")
    print(f"  positionSide: {'✅' if has_side else '❌'}")
    
    # 선물인데 position 처리 없으면 경고
    if type_str == '선물' and not has_idx and not has_side:
        print(f"  ⚠️ 선물인데 position mode 처리 없음!")
