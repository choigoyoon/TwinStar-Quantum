"""
미사용 Import 검색 스크립트
Phase 10.2.1
"""
import os
import re
import ast
from pathlib import Path

BASE = Path(r'C:\매매전략')
DIRS = ['core', 'GUI', 'exchanges', 'utils']

def get_imports(content):
    """파일에서 import 문 추출"""
    imports = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append((name, alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append((name, f'{module}.{alias.name}', node.lineno))
    except Exception:
        # Fallback to regex
        for match in re.finditer(r'^(?:from\s+\S+\s+)?import\s+(.+)$', content, re.MULTILINE):
            line = match.group(1)
            for item in line.split(','):
                item = item.strip()
                if ' as ' in item:
                    _, name = item.split(' as ')
                else:
                    name = item.split('.')[-1]
                imports.append((name.strip(), item.strip(), 0))
    return imports

def is_used(name, content, import_line):
    """import된 이름이 실제로 사용되는지 확인"""
    # Skip special cases
    if name in ['*', 'TYPE_CHECKING']:
        return True
    
    # Count occurrences (excluding import line itself)
    lines = content.split('\n')
    count = 0
    for i, line in enumerate(lines, 1):
        if i == import_line:
            continue
        # Check if name is used as word (not part of another word)
        if re.search(rf'\b{re.escape(name)}\b', line):
            count += 1
    
    return count > 0

def analyze_file(filepath):
    """단일 파일 분석"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    imports = get_imports(content)
    unused = []
    
    for name, full_import, lineno in imports:
        if not is_used(name, content, lineno):
            unused.append((name, full_import, lineno))
    
    return unused

def main():
    print('=' * 70)
    print('=== Phase 10.2.1 미사용 Import 분석 ===')
    print('=' * 70)
    print()
    
    total_unused = 0
    results = []
    
    for dir_name in DIRS:
        dir_path = BASE / dir_name
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.glob('*.py'):
            # Skip __pycache__, __init__ (re-exports)
            if py_file.name.startswith('__'):
                continue
                
            unused = analyze_file(py_file)
            if unused:
                results.append((str(py_file.relative_to(BASE)), unused))
                total_unused += len(unused)
    
    # Report
    print(f'{"파일":<40} {"미사용 Import":<30} {"줄":>5}')
    print('-' * 75)
    
    for filepath, unused_list in results:
        for name, full_import, lineno in unused_list:
            print(f'{filepath:<40} {name:<30} {lineno:>5}')
    
    print()
    print(f'총 미사용 Import: {total_unused}개')
    print()
    
    if total_unused > 0:
        print('[다음 단계]')
        print('  위 import들을 제거할 수 있습니다.')
        print('  단, __init__.py re-export와 TYPE_CHECKING은 제외됨.')

if __name__ == '__main__':
    main()
