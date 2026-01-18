import sys
import os
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print('=' * 60)
print('=== 1. 패키지 의존성 체크 ===')
print('=' * 60)
print()

# 필수 패키지
required = {
    'pandas': 'pandas',
    'numpy': 'numpy',
    'requests': 'requests',
    'websocket': 'websocket-client',
    'PyQt6': 'PyQt6',
    'pyqtgraph': 'pyqtgraph',
    'matplotlib': 'matplotlib',
}

print('[필수 패키지]')
missing_required = []
for name, pip_name in required.items():
    try:
        __import__(name.split('.')[0])
        print(f'  {name}: ✅')
    except ImportError:
        print(f'  {name}: ❌ (pip install {pip_name})')
        missing_required.append(pip_name)

print()

# 선택적 패키지
optional = {
    'numba': '속도 향상 (JIT 컴파일)',
    'ta': '기술적 분석 라이브러리',
    'ccxt': '다중 거래소 지원',
    'telegram': '텔레그램 알림',
    'aiohttp': '비동기 HTTP',
    'orjson': '빠른 JSON 처리',
    'pyarrow': 'Parquet 성능 향상'
}

print('[선택적 패키지]')
available_optional = []
missing_optional = []
for name, desc in optional.items():
    try:
        __import__(name.replace('-', '_'))
        print(f'  {name}: ✅ ({desc})')
        available_optional.append(name)
    except ImportError:
        print(f'  {name}: ❌ ({desc})')
        missing_optional.append(name)

print()
print('=' * 60)
print('=== 2. 개선 가능성 체크 ===')
print('=' * 60)
print()

improvements = {
    '성능': [
        ('numba JIT', '지표 계산 10배 속도 향상'),
        ('asyncio', '비동기 처리로 응답 속도 향상'),
        ('orjson', 'JSON 파싱 3배 빠름'),
        ('메모리 최적화', 'DataFrame 타입 최적화')
    ],
    '안정성': [
        ('재연결 로직', '웹소켓 끊김 시 자동 재연결'),
        ('헬스체크', '주기적 상태 확인'),
        ('데드맨 스위치', 'N분 무응답 시 알림'),
        ('백업 거래소', '메인 거래소 장애 시 대체')
    ],
    '기능': [
        ('다중 심볼', '여러 코인 동시 매매'),
        ('다중 전략', '전략별 독립 실행'),
        ('텔레그램 알림', '진입/청산 알림'),
        ('웹 대시보드', '원격 모니터링')
    ]
}

for category, items in improvements.items():
    print(f'[{category}]')
    for name, desc in items:
        print(f'  • {name}: {desc}')
    print()

print('=' * 60)
print('=== 3. 코드 품질 체크 ===')
print('=' * 60)
print()

files = [
    'core/unified_bot.py',
    'core/bot_state.py',
    'core/data_manager.py',
    'core/signal_processor.py',
    'core/order_executor.py',
    'core/position_manager.py',
    'core/strategy_core.py'
]

print('[파일별 분석]')
print(f'{"파일":<25} {"줄수":>8} {"함수":>6} {"클래스":>6}')
print('-' * 50)

type_hint_issues = []
for filepath in files:
    full_path = os.path.join(str(Path(__file__).parent), filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = len(content.split('\n'))
        
        funcs = len(re.findall(r'def \w+\(', content))
        classes = len(re.findall(r'class \w+', content))
        typed_funcs = len(re.findall(r'def \w+\(.*\) ->', content))
        
        name = filepath.split('/')[-1]
        print(f'{name:<25} {lines:>8} {funcs:>6} {classes:>6}')
        
        if funcs > 0 and typed_funcs / funcs < 0.3:
            type_hint_issues.append(f'{name}: {typed_funcs}/{funcs} 타입힌트')

print()
if type_hint_issues:
    print('[타입 힌트 부족 파일]')
    for issue in type_hint_issues:
        print(f'  ⚠️ {issue}')

print()
print('=' * 60)
print('=== 4. 즉시 적용 가능한 개선 ===')
print('=' * 60)
print()

quick_wins = [
    ('pip install orjson', 'JSON 처리 3배 빠름', '1분'),
    ('pip install pyarrow', 'Parquet 처리 빠름', '1분'),
    ('requirements.txt 생성', '패키지 관리', '5분'),
    ('로그 레벨 조정', 'DEBUG → INFO', '즉시'),
]

print(f'{"작업":<30} {"효과":<25} {"시간":<10}')
print('-' * 65)
for task, effect, time in quick_wins:
    print(f'{task:<30} {effect:<25} {time:<10}')

print()
print('=' * 60)
print('=== 요약 ===')
print('=' * 60)
print()
print(f'필수 패키지 누락: {len(missing_required)}개')
print(f'선택 패키지 설치됨: {len(available_optional)}/{len(optional)}개')
print(f'타입힌트 부족: {len(type_hint_issues)}개 파일')
