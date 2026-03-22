#!/usr/bin/env python3
"""타임프레임 계층 검증 테스트"""

import sys
from pathlib import Path

# 프로젝트 루트
sys.path.insert(0, str(Path(__file__).parent))

from config.parameters import validate_tf_hierarchy, get_valid_filter_tfs, TIMEFRAME_ORDER

print('=' * 60)
print('🔍 타임프레임 계층 검증 테스트')
print('=' * 60)

# 1. TIMEFRAME_ORDER 확인
print(f'\n1. TIMEFRAME_ORDER: {TIMEFRAME_ORDER}')

# 2. get_valid_filter_tfs 테스트
print('\n2. get_valid_filter_tfs() 테스트:')
for entry in ['15m', '1h', '4h']:
    valid_tfs = get_valid_filter_tfs(entry)
    print(f'   entry_tf="{entry}" -> {valid_tfs}')

# 3. validate_tf_hierarchy 테스트
print('\n3. validate_tf_hierarchy() 테스트:')
test_cases = [
    ('1h', '4h', True),
    ('1h', '6h', True),
    ('1h', '8h', True),
    ('1h', '15m', False),
    ('15m', '1h', True),
    ('15m', '15m', False),
]

all_passed = True
for entry, filter_tf, expected in test_cases:
    result = validate_tf_hierarchy(entry, filter_tf)
    status = '✅' if result == expected else '❌'
    if result != expected:
        all_passed = False
    print(f'   {status} entry="{entry}", filter="{filter_tf}" -> {result} (예상: {expected})')

print('\n' + ('✅ 모든 테스트 통과!' if all_passed else '❌ 일부 테스트 실패'))
