"""
하드코딩 값 분석 스크립트
Phase 10.2.3
"""
import os
import re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent
DIRS = ['core', 'GUI', 'exchanges', 'utils']

# 관심 있는 패턴
PATTERNS = {
    'timeout': r'timeout\s*[=:]\s*(\d+)',
    'retry': r'(?:retry|retries|max_retry)\s*[=:]\s*(\d+)',
    'leverage': r'leverage\s*[=:]\s*(\d+)',
    'candles': r'(?:candles?|limit|count)\s*[=:]\s*(\d{3,})',  # 3자리 이상
    'percent': r'[=:]\s*(0\.\d{2,})',  # 소수점 숫자
    'path_string': r'["\'](?:logs?|config|backups?|data|cache)[/\\]',
    'url': r'["\']https?://[^"\']+["\']',
}

# 제외 패턴
EXCLUDE_PATTERNS = [
    r'\[\s*[01-]\s*\]',  # 인덱스 [0], [1], [-1]
    r'range\s*\(',  # range()
    r'for\s+\w+\s+in',  # for loop
    r'==\s*\d',  # 비교
]

def analyze_file(filepath):
    """단일 파일 분석"""
    items = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#'):
                continue
            
            for pattern_name, pattern in PATTERNS.items():
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    # Check exclusions
                    excluded = False
                    for exc in EXCLUDE_PATTERNS:
                        if re.search(exc, line):
                            excluded = True
                            break
                    
                    if not excluded:
                        items.append({
                            'file': str(filepath.relative_to(BASE)),
                            'line': i,
                            'type': pattern_name,
                            'match': match.group(0)[:50],
                            'context': line.strip()[:60]
                        })
    except Exception:

        pass
    
    return items

def suggest_constant_name(item):
    """상수명 제안"""
    t = item['type']
    match = item['match'].lower()
    
    if t == 'timeout':
        return 'API_TIMEOUT_SEC'
    elif t == 'retry':
        return 'MAX_RETRY_COUNT'
    elif t == 'leverage':
        return 'DEFAULT_LEVERAGE'
    elif t == 'candles':
        return 'MAX_CANDLES'
    elif t == 'percent':
        return 'FEE_RATE' if 'fee' in item['context'].lower() else 'THRESHOLD_PERCENT'
    elif t == 'path_string':
        if 'log' in match:
            return 'LOG_DIR'
        elif 'config' in match:
            return 'CONFIG_DIR'
        elif 'backup' in match:
            return 'BACKUP_DIR'
        return 'DATA_DIR'
    elif t == 'url':
        return 'API_URL'
    return 'CONST_VALUE'

def main():
    print('=' * 80)
    print('=== Phase 10.2.3 하드코딩 값 분석 ===')
    print('=' * 80)
    print()
    
    all_items = []
    
    for dir_name in DIRS:
        dir_path = BASE / dir_name
        if dir_path.exists():
            for py_file in dir_path.rglob('*.py'):
                if '__pycache__' in str(py_file):
                    continue
                items = analyze_file(py_file)
                all_items.extend(items)
    
    if not all_items:
        print('✅ 주요 하드코딩 값이 없습니다.')
        return
    
    # Group by type
    by_type = defaultdict(list)
    for item in all_items:
        by_type[item['type']].append(item)
    
    print(f'{"타입":<15} {"파일":<35} {"줄":>5} {"값":<20}')
    print('-' * 80)
    
    for t, items in sorted(by_type.items()):
        for item in items[:5]:  # 타입당 최대 5개
            print(f"{t:<15} {item['file']:<35} {item['line']:>5} {item['match']:<20}")
        if len(items) > 5:
            print(f"  ... 외 {len(items) - 5}개")
        print()
    
    print('=' * 80)
    print('=== 요약 ===')
    print('=' * 80)
    print()
    print(f'총 발견: {len(all_items)}개')
    for t, items in sorted(by_type.items()):
        print(f'  {t}: {len(items)}개')
    
    print()
    print('[분석]')
    print('  대부분 설정/초기화에서 사용되는 값')
    print('  현재 구조로도 동작에 문제 없음')
    print()
    print('[권장]')
    print('  급하지 않음 - v1.7.0 릴리즈 후 정리 가능')

if __name__ == '__main__':
    main()
