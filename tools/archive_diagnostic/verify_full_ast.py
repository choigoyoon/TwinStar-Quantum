# verify_full_ast.py - 전체 파일 AST 검증
import ast
from pathlib import Path

base = Path(__file__).parent

print("=" * 60)
print("전체 Python 파일 AST 검증")
print("=" * 60)

all_py = list(base.rglob('*.py'))
all_py = [p for p in all_py if not any(x in str(p) for x in ['__pycache__', 'venv', 'build', 'dist', '.git', '_backup'])]

print(f"총 파일: {len(all_py)}개\n")

errors = []
warnings = []
success = 0

for py in all_py:
    rel = str(py.relative_to(base))
    try:
        code = py.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(code)
        success += 1
        
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name in funcs:
                    warnings.append(f"{rel}: 중복 {node.name}()")
                funcs[node.name] = node.lineno
            
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == 'eval':
                        errors.append(f"{rel} L{node.lineno}: eval()")
            
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value == True:
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
                    if not has_break and not has_return:
                        errors.append(f"{rel} L{node.lineno}: 무한루프")
                        
    except SyntaxError as e:
        errors.append(f"{rel} L{e.lineno}: 문법에러")
    except Exception as e:
        errors.append(f"{rel}: 파싱실패")

folders = {}
for py in all_py:
    folder = py.parent.name if py.parent != base else 'root'
    folders[folder] = folders.get(folder, 0) + 1

print("폴더별:")
for folder, count in sorted(folders.items(), key=lambda x: -x[1])[:10]:
    print(f"  {folder}: {count}")

print(f"\n" + "=" * 60)
print(f"결과: {success}/{len(all_py)} 통과")
print("=" * 60)

print(f"\n에러: {len(errors)}개")
for e in errors[:20]:
    print(f"  {e}")

print(f"\n경고: {len(warnings)}개")
for w in warnings[:10]:
    print(f"  {w}")

print()
if errors:
    print("X 에러 수정 필요")
else:
    print("OK 전체 AST 검증 통과")
