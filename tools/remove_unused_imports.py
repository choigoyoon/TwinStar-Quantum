"""
미사용 Import 자동 제거 스크립트
Phase 10.2.1
"""
import os
import re
import ast
from pathlib import Path

BASE = Path(rstr(Path(__file__).parent))
DIRS = ['core', 'GUI', 'exchanges', 'utils']

def get_imports_with_lines(content):
    """파일에서 import 문과 라인 번호 추출"""
    imports = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            imports.append((i, line, stripped))
    
    return imports

def extract_names_from_import(import_line):
    """import 문에서 import된 이름들 추출"""
    names = []
    line = import_line.strip()
    
    # from X import Y, Z
    if line.startswith('from '):
        match = re.match(r'from\s+\S+\s+import\s+(.+)', line)
        if match:
            imports_part = match.group(1)
            # Handle parentheses
            if '(' in imports_part:
                return []  # Skip multi-line for now
            for item in imports_part.split(','):
                item = item.strip()
                if ' as ' in item:
                    _, name = item.split(' as ')
                    names.append(name.strip())
                else:
                    names.append(item.strip())
    # import X, Y
    else:
        match = re.match(r'import\s+(.+)', line)
        if match:
            for item in match.group(1).split(','):
                item = item.strip()
                if ' as ' in item:
                    _, name = item.split(' as ')
                    names.append(name.strip())
                else:
                    names.append(item.split('.')[0].strip())
    
    return [n for n in names if n and n != '*']

def is_name_used(name, content, import_lineno):
    """import된 이름이 실제로 사용되는지 확인"""
    if name in ['*', 'TYPE_CHECKING', 'annotations']:
        return True
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if i == import_lineno:
            continue
        # Check if name is used (word boundary)
        if re.search(rf'\b{re.escape(name)}\b', line):
            return True
    return False

def remove_unused_from_import(import_line, unused_names):
    """import 문에서 미사용 이름만 제거"""
    if not unused_names:
        return import_line
    
    line = import_line.strip()
    
    # from X import Y, Z → from X import Z (if Y unused)
    if line.startswith('from '):
        match = re.match(r'(from\s+\S+\s+import\s+)(.+)', line)
        if match:
            prefix = match.group(1)
            imports_part = match.group(2)
            
            items = [i.strip() for i in imports_part.split(',')]
            kept = []
            for item in items:
                name = item.split(' as ')[-1].strip() if ' as ' in item else item.strip()
                if name not in unused_names:
                    kept.append(item)
            
            if kept:
                # Preserve original indentation
                indent = len(import_line) - len(import_line.lstrip())
                return ' ' * indent + prefix + ', '.join(kept)
            else:
                return None  # Remove entire line
    
    return import_line

def process_file(filepath):
    """단일 파일 처리"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    lines = content.split('\n')
    imports = get_imports_with_lines(content)
    
    removed_count = 0
    lines_to_remove = set()
    line_replacements = {}
    
    for lineno, original_line, stripped in imports:
        names = extract_names_from_import(stripped)
        unused = [n for n in names if not is_name_used(n, content, lineno)]
        
        if unused:
            if set(unused) == set(names):
                # All names unused - remove entire line
                lines_to_remove.add(lineno)
                removed_count += len(unused)
            else:
                # Some names unused - keep used ones
                new_line = remove_unused_from_import(original_line, unused)
                if new_line:
                    line_replacements[lineno] = new_line
                else:
                    lines_to_remove.add(lineno)
                removed_count += len(unused)
    
    if removed_count == 0:
        return 0
    
    # Apply changes
    new_lines = []
    for i, line in enumerate(lines):
        if i in lines_to_remove:
            continue
        elif i in line_replacements:
            new_lines.append(line_replacements[i])
        else:
            new_lines.append(line)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(new_lines))
    
    return removed_count

def main():
    print('=' * 70)
    print('=== Phase 10.2.1 미사용 Import 자동 제거 ===')
    print('=' * 70)
    print()
    
    total_removed = 0
    results = []
    
    for dir_name in DIRS:
        dir_path = BASE / dir_name
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.glob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            removed = process_file(py_file)
            if removed > 0:
                results.append((str(py_file.relative_to(BASE)), removed))
                total_removed += removed
    
    print(f'{"파일":<45} {"제거됨":>8}')
    print('-' * 55)
    
    for filepath, count in sorted(results, key=lambda x: -x[1]):
        print(f'{filepath:<45} {count:>8}')
    
    print()
    print(f'총 제거된 Import: {total_removed}개')
    print()
    print('✅ 제거 완료. 검증 실행 권장.')

if __name__ == '__main__':
    main()
