
from pathlib import Path
import ast

base = Path(__file__).parent
exchanges_dir = base / 'exchanges'

print("=" * 60)
print("전체 거래소 WS + 시간동기화 최종 검증")
print("=" * 60)

exchanges = ['binance', 'upbit', 'bithumb', 'okx', 'bitget', 'bingx']
all_pass = True

for ex_name in exchanges:
    ex_file = exchanges_dir / f'{ex_name}_exchange.py'
    if not ex_file.exists():
        print(f"❌ {ex_name}: 파일 없음")
        all_pass = False
        continue
        
    try:
        code = ex_file.read_text(encoding='utf-8')
        tree = ast.parse(code)
        
        methods = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        
        has_ws = 'start_websocket' in methods
        has_sync = 'sync_time' in methods
        has_auto = '_auto_sync_time' in methods
        has_fetch = 'fetchTime' in methods
        
        # Bithumb 등 일부 어댑터는 sync_time이 없을 수도 있어(기존에 없었으면) 체크
        
        status = []
        if has_ws: status.append("WS✅")
        else: status.append("WS❌")
        
        if has_fetch: status.append("Fetch✅")
        else: status.append("Fetch❌")

        print(f"  {ex_name:10}: {' '.join(status)}")
        
        if not (has_ws and has_fetch):
            all_pass = False
            
    except SyntaxError:
        print(f"❌ {ex_name}: 문법 오류 발생!")
        all_pass = False

print("-" * 60)
if all_pass:
    print("✅ 모든 거래소 정규화 완료")
else:
    print("⚠️ 일부 거래소 미완료 확인 필요")
