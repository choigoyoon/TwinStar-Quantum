# verify_ast.py - AST 기반 정밀 검증
import ast
from pathlib import Path

base = Path(r'C:\매매전략')

print("=" * 60)
print("AST 기반 정밀 검증")
print("=" * 60)

errors = []
warnings = []

critical = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'core/updater.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'exchanges/ws_handler.py',
    'GUI/staru_main.py'
]

for rel in critical:
    fpath = base / rel
    if not fpath.exists():
        errors.append(f"X 파일 없음: {rel}")
        continue
    
    try:
        code = fpath.read_text(encoding='utf-8')
        tree = ast.parse(code)
    except SyntaxError as e:
        errors.append(f"X 문법 에러: {rel} L{e.lineno}")
        continue
    except Exception as e:
        errors.append(f"X 파싱 실패: {rel}")
        continue
    
    print(f"\n{rel}")
    
    functions = {}
    classes = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            name = node.name
            if name in functions:
                warnings.append(f"! 중복 함수: {rel} - {name}()")
            functions[name] = node.lineno
        
        if isinstance(node, ast.ClassDef):
            if node.name in classes:
                warnings.append(f"! 중복 클래스: {rel} - {node.name}")
            classes[node.name] = node.lineno
        
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'eval':
                errors.append(f"X eval(): {rel} L{node.lineno}")
        
        if isinstance(node, ast.While):
            if isinstance(node.test, ast.Constant) and node.test.value == True:
                has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                if not has_break:
                    errors.append(f"X 무한루프: {rel} L{node.lineno}")
        
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                warnings.append(f"! bare except: {rel} L{node.lineno}")
    
    print(f"  클래스: {len(classes)}개, 함수: {len(functions)}개")
    
    if 'unified_bot' in rel:
        for r in ['execute_entry', '_execute_live_close', '_on_candle_close']:
            if r in functions:
                print(f"  OK {r}() L{functions[r]}")
            else:
                errors.append(f"X 필수 함수 없음: {r}()")
    
    if 'strategy_core' in rel:
        for r in ['detect_signal', 'run_backtest']:
            if r in functions:
                print(f"  OK {r}() L{functions[r]}")
            else:
                errors.append(f"X 필수 함수 없음: {r}()")

print("\n" + "=" * 60)
print(f"에러: {len(errors)}개, 경고: {len(warnings)}개")
print("=" * 60)

for e in errors:
    print(f"  {e}")

for w in warnings[:10]:
    print(f"  {w}")
if len(warnings) > 10:
    print(f"  ... 외 {len(warnings)-10}개")

print()
if errors:
    print("X 에러 수정 필요")
else:
    print("OK AST 정밀 검증 통과")
