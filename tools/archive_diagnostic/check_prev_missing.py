import os

# 1. 이전에 누락 보고된 9개 모듈 체크
missing_reported = [
    'core.auto_optimizer',
    'utils.time_utils', 
    'utils.cache_cleaner',
    'utils.error_reporter',
    'utils.api_utils',
    'utils.data_utils',
    'utils.preset_manager',
    'utils.new_coin_detector',
    'exchanges.exchange_manager'
]

with open('staru_clean.spec', 'r', encoding='utf-8') as f:
    spec = f.read()

print('=== 이전 누락 보고 모듈 - Spec 포함 여부 ===')
for m in missing_reported:
    status = '✅ 포함' if m in spec else '❌ 누락'
    print(f'{status} {m}')

# 2. 실제 파일 존재 여부 확인
modules_paths = [
    'core/auto_optimizer.py',
    'utils/time_utils.py',
    'utils/cache_cleaner.py', 
    'utils/error_reporter.py',
    'utils/api_utils.py',
    'utils/data_utils.py',
    'utils/preset_manager.py',
    'utils/new_coin_detector.py',
    'exchanges/exchange_manager.py'
]

print('\n=== 파일 존재 여부 ===')
for m in modules_paths:
    exists = os.path.exists(m)
    status = '✅ 존재' if exists else '❌ 없음'
    print(f'{status} {m}')
