"""
TODO/FIXME 분석 스크립트
Phase 10.2.4
"""
import os
import re
from pathlib import Path

BASE = Path(__file__).parent
DIRS = ['core', 'GUI', 'exchanges', 'utils', 'storage', 'config']
PATTERNS = ['TODO', 'FIXME', 'XXX', 'HACK']

def search_todos():
    """모든 파일에서 TODO/FIXME 검색"""
    results = []
    
    # Search specified directories
    for dir_name in DIRS:
        dir_path = BASE / dir_name
        if dir_path.exists():
            for py_file in dir_path.rglob('*.py'):
                results.extend(search_file(py_file))
    
    # Search root .py files
    for py_file in BASE.glob('*.py'):
        results.extend(search_file(py_file))
    
    return results

def search_file(filepath):
    """단일 파일에서 TODO/FIXME 검색"""
    items = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            for pattern in PATTERNS:
                if pattern in line.upper():
                    # Extract the comment content
                    content = line.strip()
                    if len(content) > 80:
                        content = content[:77] + '...'
                    items.append({
                        'file': str(filepath.relative_to(BASE)),
                        'line': i,
                        'type': pattern,
                        'content': content
                    })
                    break
    except Exception:

        pass
    
    return items

def classify_item(item):
    """항목 분류"""
    content = item['content'].lower()
    
    # 완료됨 패턴
    if 'done' in content or 'completed' in content or 'fixed' in content:
        return '완료됨'
    
    # 중요 패턴
    if any(k in content for k in ['bug', 'security', 'crash', 'critical', 'error', 'fix']):
        return '중요'
    
    # 사소 패턴
    if any(k in content for k in ['refactor', 'cleanup', 'optimize', 'improve', 'maybe', 'later']):
        return '사소'
    
    return '검토필요'

def main():
    print('=' * 80)
    print('=== Phase 10.2.4 TODO/FIXME 분석 ===')
    print('=' * 80)
    print()
    
    results = search_todos()
    
    if not results:
        print('✅ TODO/FIXME 항목이 없습니다.')
        return
    
    # Classify
    for item in results:
        item['classification'] = classify_item(item)
    
    # Display
    print(f'{"파일":<35} {"줄":>5} {"타입":<6} {"분류":<10}')
    print('-' * 80)
    
    for item in sorted(results, key=lambda x: (x['classification'], x['file'])):
        print(f"{item['file']:<35} {item['line']:>5} {item['type']:<6} {item['classification']:<10}")
        print(f"   → {item['content'][:70]}")
    
    print()
    print('=' * 80)
    print('=== 요약 ===')
    print('=' * 80)
    
    # Count by classification
    counts = {}
    for item in results:
        c = item['classification']
        counts[c] = counts.get(c, 0) + 1
    
    print(f'총 발견: {len(results)}개')
    for c, n in sorted(counts.items()):
        print(f'  {c}: {n}개')
    
    print()
    print('[권장 조치]')
    print('  완료됨 → 주석 제거')
    print('  중요 → task.md 추가')
    print('  사소/검토필요 → 유지 또는 제거')

if __name__ == '__main__':
    main()
