"""내부 임포트 체인 검증"""

import sys
import ast
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

SCAN_DIRS = ["core", "exchanges", "utils"]

def get_internal_imports(filepath):
    """파일에서 내부 임포트 추출"""
    imports = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(tuple(SCAN_DIRS)):
                        imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(tuple(SCAN_DIRS)):
                    imports.append(node.module)
    except Exception:

        pass
    return imports

def run():
    """임포트 검증 실행"""
    import importlib
    
    passed = 0
    failed = 0
    errors = []
    
    for folder in SCAN_DIRS:
        folder_path = ROOT / folder
        if not folder_path.exists():
            continue
        
        print(f"\n[{folder.upper()}]")
        
        for py_file in folder_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            imports = get_internal_imports(py_file)
            rel_path = py_file.relative_to(ROOT)
            
            for imp in imports:
                try:
                    importlib.import_module(imp)
                    passed += 1
                except Exception as e:
                    print(f"  ❌ {rel_path} → {imp}")
                    failed += 1
                    errors.append((f"{rel_path}→{imp}", str(e)))
    
    print(f"\n  검사: {passed + failed}개 임포트")
    
    return {'passed': passed, 'failed': failed, 'errors': errors}

if __name__ == "__main__":
    result = run()
    print(f"\n결과: {result['passed']}/{result['passed']+result['failed']}")
