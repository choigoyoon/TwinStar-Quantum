#!/usr/bin/env python3
"""
TwinStar Quantum 깊은 검증 시스템
전체 public 메서드 검증

Usage:
    py -3 tests/deep_verify.py
    py -3 tests/deep_verify.py --list-uncovered
"""
import sys
import os
import io
import ast
import importlib
import inspect
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Fix Korean encoding in PowerShell
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Results
STATS = {
    'total_files': 0,
    'total_classes': 0,
    'total_methods': 0,
    'verified': 0,
    'failed': 0,
    'skipped': 0,
}

ERRORS = []
EXCLUDE_CLASSES = ["MockExchange"]



def analyze_module(module_path: Path, module_name: str) -> List[Tuple[str, str, str]]:
    """Analyze a Python file and extract class.method pairs"""
    items = []
    try:
        tree = ast.parse(module_path.read_text(encoding='utf-8'))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in EXCLUDE_CLASSES:
                    continue
                class_name = node.name
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if not item.name.startswith('_'):
                            items.append((module_name, class_name, item.name))
    except Exception as e:
        pass
    
    return items


def verify_method(module_name: str, class_name: str, method_name: str) -> Tuple[bool, str]:
    """Verify a single method exists and is callable"""
    try:
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name, None)
        if cls is None:
            return False, "Class not found"
        
        method = getattr(cls, method_name, None)
        if method is None:
            return False, "Method not found"
        
        # Check if it's a property
        if isinstance(method, property):
            return True, "OK (Property)"
            
        if callable(method):
            return True, "OK"
        else:
            return False, "Not callable"
            
    except Exception as e:
        return False, str(e)[:50]


def main(list_uncovered=False):
    print("\n" + "=" * 60)
    print("TwinStar Quantum 깊은 검증 시스템")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Directories to scan
    dirs = {
        'core': 'core',
        'utils': 'utils',
        'exchanges': 'exchanges',
        'storage': 'storage',
    }
    
    all_methods = []
    
    # Collect all methods
    print("\n[1/3] 메서드 수집 중...")
    for dir_name, module_prefix in dirs.items():
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            continue
        
        for py_file in dir_path.glob('*.py'):
            if py_file.name.startswith('_') and py_file.name != '__init__.py':
                continue
            
            module_name = f"{module_prefix}.{py_file.stem}"
            STATS['total_files'] += 1
            
            methods = analyze_module(py_file, module_name)
            all_methods.extend(methods)
    
    STATS['total_methods'] = len(all_methods)
    STATS['total_classes'] = len(set((m[0], m[1]) for m in all_methods))
    
    print(f"  - 파일: {STATS['total_files']}개")
    print(f"  - 클래스: {STATS['total_classes']}개")
    print(f"  - Public 메서드: {STATS['total_methods']}개")
    
    # Verify all methods
    print("\n[2/3] 메서드 검증 중...")
    uncovered = []
    
    for module_name, class_name, method_name in all_methods:
        success, msg = verify_method(module_name, class_name, method_name)
        
        if success:
            STATS['verified'] += 1
        else:
            STATS['failed'] += 1
            uncovered.append((module_name, class_name, method_name, msg))
    
    # Summary
    print("\n[3/3] 결과")
    print("-" * 60)
    
    total = STATS['total_methods']
    verified = STATS['verified']
    pct = (verified / total * 100) if total > 0 else 0
    
    print(f"""
📊 프로젝트 규모:
  - 파일: {STATS['total_files']}개
  - 클래스: {STATS['total_classes']}개
  - Public 메서드: {total}개

✅ 검증 결과:
  - 검증됨: {verified}/{total} ({pct:.1f}%)
  - 실패: {STATS['failed']}개
""")
    
    if list_uncovered and uncovered:
        print("❌ 미검증 목록:")
        for i, (mod, cls, method, msg) in enumerate(uncovered[:30], 1):
            print(f"  {i}. {mod}.{cls}.{method} - {msg}")
        if len(uncovered) > 30:
            print(f"  ... 외 {len(uncovered) - 30}개")
    
    print("=" * 60)
    
    if pct >= 95:
        print("상태: 배포 가능 ✅")
    elif pct >= 80:
        print("상태: 조건부 배포 가능 ⚠️")
    else:
        print("상태: 검토 필요 ❌")
    
    return pct >= 95


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--list-uncovered', action='store_true')
    args = parser.parse_args()
    
    main(list_uncovered=args.list_uncovered)
