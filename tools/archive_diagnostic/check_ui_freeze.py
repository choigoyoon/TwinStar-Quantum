from pathlib import Path
import re

base = Path(__file__).parent

print('=' * 70)
print('🔧 UI Freeze 수정')
print('=' * 70)

#############################################
# [1] data_collector_widget.py 분석
#############################################
print('\n[1] data_collector_widget.py 분석')
print('-' * 70)

dc_file = base / 'GUI' / 'data_collector_widget.py'
if dc_file.exists():
    code = dc_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    # 문제 패턴 찾기
    issues = []
    for i, line in enumerate(lines):
        if 'requests.get' in line or 'requests.post' in line:
            # 상위 20줄에 QThread/Worker 있는지 확인
            context = '\n'.join(lines[max(0,i-20):i])
            if 'QThread' not in context and 'Worker' not in context and 'Thread' not in context:
                issues.append((i+1, line.strip()[:60]))
    
    if issues:
        print(f'  ⚠️ 동기 API 호출 {len(issues)}건:')
        for ln, code_line in issues[:5]:
            print(f'    L{ln}: {code_line}')
    else:
        print('  ✅ 문제 없음 또는 이미 수정됨')
    
    # 이미 Worker 있는지 확인
    has_worker = 'class.*Worker.*QThread' in code or 'DownloadThread' in code
    print(f'  Worker 클래스: {"✅ 있음" if has_worker else "❌ 없음"}')

#############################################
# [2] settings_widget.py 분석
#############################################
print('\n[2] settings_widget.py 분석')
print('-' * 70)

sw_file = base / 'GUI' / 'settings_widget.py'
if sw_file.exists():
    code = sw_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    # _test_connection 함수 찾기
    test_func = None
    for i, line in enumerate(lines):
        if 'def _test_connection' in line or 'def test_connection' in line:
            test_func = i + 1
            break
    
    if test_func:
        # 함수 내용 확인 (다음 30줄)
        func_body = '\n'.join(lines[test_func:test_func+30])
        if 'QThread' in func_body or 'Worker' in func_body:
            print(f'  ✅ L{test_func}: 이미 비동기화됨')
        else:
            print(f'  ⚠️ L{test_func}: 동기 호출 (수정 필요)')
    else:
        print('  ℹ️ _test_connection 함수 없음')
    
    # connect_exchange 호출 확인
    connect_calls = [i+1 for i, l in enumerate(lines) if 'connect_exchange' in l]
    print(f'  connect_exchange 호출: {len(connect_calls)}곳')

#############################################
# [3] 수정 권장사항 출력
#############################################
print('\n' + '=' * 70)
print('📋 수정 권장사항')
print('=' * 70)
print('''
1. data_collector_widget.py:
   - _get_binance_top10, _select_top_gainers 등에서
   - requests.get() 호출을 QThread Worker로 이동

2. settings_widget.py:
   - _test_connection에서 connect_exchange() 호출을
   - QThread Worker로 이동

3. 공통:
   - UI에 "조회중..." 표시 추가
   - 실패 시 에러 메시지 표시
''')
print('=' * 70)
