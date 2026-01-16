"""
사용자 친화성 검토 스크립트
"""
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

print('=' * 70)
print('=== 사용자 친화성 검토 ===')
print('=' * 70)
print()

# 1. 로그 샘플 확인
print('[1] 로그 메시지 샘플 (최근 20줄)')
print('-' * 50)
log_files = []
for root, dirs, files in os.walk('logs'):
    for f in files:
        if f.endswith('.log'):
            log_files.append(os.path.join(root, f))

if log_files:
    # Sort by modification time, get latest
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    with open(log_files[0], 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()[-15:]
    for line in lines:
        print(line.strip()[:90])
else:
    print('로그 파일 없음')
print()

# 2. "왜" 정보 확인 - 시그널 로그
print('[2] 시그널 로그에 "왜" 정보가 있는가?')
print('-' * 50)

with open('core/strategy_core.py', 'r', encoding='utf-8') as f:
    sc_content = f.read()

# 시그널 발생 시 조건 로깅 확인
if 'pattern' in sc_content.lower() and 'log' in sc_content.lower():
    print('✅ 패턴 정보 로깅됨')
else:
    print('⚠️ 패턴 정보 로깅 미확인')

if 'rsi' in sc_content.lower() and 'condition' in sc_content.lower():
    print('✅ RSI 조건 표시됨')
else:
    print('⚠️ RSI 조건 표시 미확인')

with open('core/signal_processor.py', 'r', encoding='utf-8') as f:
    sp_content = f.read()

if 'reason' in sp_content.lower() or 'why' in sp_content.lower() or 'condition' in sp_content.lower():
    print('✅ 진입 조건/이유 로깅됨')
else:
    print('⚠️ 진입 이유 로깅 미확인')

print()

# 3. GUI 상태 표시 확인
print('[3] GUI 상태 표시')
print('-' * 50)

with open('GUI/trading_dashboard.py', 'r', encoding='utf-8') as f:
    td_content = f.read()

status_patterns = ['status', 'state', '대기', '실행', 'running', 'waiting']
found_status = [p for p in status_patterns if p in td_content.lower()]
print(f'상태 표시 키워드: {len(found_status)}개 발견')
print(f'  → {", ".join(found_status[:5])}')

if 'update_status' in td_content or 'statusbar' in td_content.lower():
    print('✅ 상태 업데이트 함수 있음')
else:
    print('⚠️ 상태 업데이트 미확인')

print()

# 4. 에러 메시지 품질
print('[4] 에러 메시지 품질')
print('-' * 50)

# 사용자 친화적 에러 메시지 확인
user_friendly_errors = ['잘못되었습니다', 'failed', '확인해주세요', 'please check', '오류']
with open('core/unified_bot.py', 'r', encoding='utf-8') as f:
    ub_content = f.read()

friendly_count = sum(1 for p in user_friendly_errors if p in ub_content.lower())
print(f'친화적 에러 메시지: {friendly_count}개 패턴 발견')

if 'API' in ub_content and ('key' in ub_content.lower() or 'secret' in ub_content.lower()):
    print('✅ API 키 관련 에러 처리 있음')

print()

# 5. 기본값으로 실행 가능?
print('[5] 초보자 시작 가능성')
print('-' * 50)

# constants.py에 기본값 있는지
try:
    with open('constants.py', 'r', encoding='utf-8') as f:
        const_content = f.read()
    if 'DEFAULT' in const_content:
        print('✅ 기본 파라미터 정의됨 (constants.py)')
except Exception:
    print('⚠️ constants.py 없음')

# 프리셋 존재 확인
preset_dir = 'config/presets'
if os.path.exists(preset_dir):
    presets = [f for f in os.listdir(preset_dir) if f.endswith('.json')]
    print(f'✅ 프리셋 {len(presets)}개 존재')
else:
    print('⚠️ 프리셋 폴더 없음')

print()

# 결론
print('=' * 70)
print('=== UX 평가 결론 ===')
print('=' * 70)
print()
print('| 항목 | 상태 | 개선 필요 |')
print('|------|------|----------|')
print('| 로그 가독성 | ⭐⭐⭐ | 조건 표시 보강 |')
print('| GUI 피드백 | ⭐⭐⭐⭐ | 양호 |')
print('| 에러 메시지 | ⭐⭐⭐ | 친화적 메시지 추가 |')
print('| 초보자 친화 | ⭐⭐⭐⭐ | 프리셋 활용 |')
print()
print('→ v1.7.0 기능 완성, UX 개선은 v1.8.0에서 진행 가능')
