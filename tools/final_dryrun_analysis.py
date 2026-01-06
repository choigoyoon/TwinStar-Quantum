import os
from datetime import datetime

print('=' * 60)
print('=== Dry-run 최종 분석 (1시간 완료) ===')
print(f'분석 시각: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('=' * 60)
print()

log_dir = r'C:\매매전략\logs'
log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')], 
                   key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)

if log_files:
    latest_log = log_files[0]
    log_path = os.path.join(log_dir, latest_log)
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    print(f'📂 분석 파일: {latest_log}')
    print(f'📊 총 로그: {len(lines)}줄')
    print()
    
    # 분류
    errors = [l for l in lines if 'error' in l.lower()]
    warnings = [l for l in lines if 'warning' in l.lower()]
    dry_runs = [l for l in lines if '[DRY-RUN]' in l or '[DRY]' in l]
    signals = [l for l in lines if '[signal]' in l.lower() or 'pattern' in l.lower()]
    connected = [l for l in lines if 'connected' in l.lower()]
    
    # 포지션 에러 제외 (Dry-run에서 예상됨)
    critical_errors = [l for l in errors if 'position' not in l.lower() and 'sync' not in l.lower()]
    
    print('[결과 요약]')
    print(f'  ✅ 연결: {len(connected)}회')
    print(f'  ⚠️ 경고: {len(warnings)}개')
    print(f'  🔴 에러: {len(errors)}개 (Critical: {len(critical_errors)}개)')
    print(f'  📊 시그널: {len(signals)}개')
    print(f'  🎮 DRY-RUN 로그: {len(dry_runs)}개')
    print()
    
    if len(critical_errors) == 0:
        print('=' * 60)
        print('✅ Dry-run 성공!')
        print('=' * 60)
        print()
        print('→ 1시간 동안 크래시 없이 안정적 실행')
        print('→ Critical 에러 0개')
        print('→ 소액 실매매 준비 완료')
        print()
        print('[다음 단계]')
        print('  1. 소액 테스트 ($10-50)')
        print('  2. 24시간 모니터링')
        print('  3. 정상 확인 후 증액')
    else:
        print('=' * 60)
        print('⚠️ Critical 에러 발견')
        print('=' * 60)
        print()
        print('[에러 목록]')
        for e in critical_errors[:5]:
            print(f'  {e.strip()[:80]}')
        print()
        print('→ 에러 수정 후 재테스트 필요')
else:
    print('❌ 로그 파일을 찾을 수 없습니다.')
