import os
import glob
from datetime import datetime

def analyze_logs():
    log_dir = r'C:\매매전략\logs'
    # Find all .log files
    all_files = glob.glob(os.path.join(log_dir, '*.log'))
    if not all_files:
        print(f"❌ No log files found in {log_dir}")
        return

    # Sort by modification time
    sorted_files = sorted(all_files, key=os.path.getmtime)
    
    # Analyze last 2 files (current and previous)
    target_files = sorted_files[-2:]
    
    print('=== Dry-run 최종 분석 (Virtual Mode) ===')
    print(f'분석 대상: {[os.path.basename(f) for f in target_files]}')
    print()

    for log_path in target_files:
        filename = os.path.basename(log_path)
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

        # Filter lines for Virtual Mode check
        errors = [l for l in lines if 'error' in l.lower()]
        dry_entries = [l for l in lines if '[DRY-RUN]' in l and '진입' in l] # Matches [DRY-RUN] 가상 진입
        dry_exits = [l for l in lines if '[DRY-RUN]' in l and '청산' in l]   # Matches [DRY-RUN] 가상 청산
        signals = [l for l in lines if '[signal]' in l.lower() or 'pattern detected' in l.lower()]
        
        # Check connection success
        connected = any('Bybit connected' in l or 'Connected to bybit' in l for l in lines)
        virtual_sync = any('[SYNC] (DRY)' in l for l in lines)

        print(f'[{filename}]')
        print(f'  총 로그: {len(lines)}줄')
        print(f'  연결 상태: {"✅ 성공" if connected else "❓ 확인 필요"}')
        print(f'  가상 동기화: {"✅ 확인됨" if virtual_sync else "❓ 미확인"}')
        print(f'  에러: {len(errors)}개')
        print(f'  가상 진입: {len(dry_entries)}개')
        print(f'  가상 청산: {len(dry_exits)}개')
        print(f'  시그널: {len(signals)}개')
        
        if len(errors) == 0:
            print('  ✅ 에러 없음 (Clean)')
        else:
            print('  ⚠️ 에러 발견:')
            for e in errors[:3]:
                print(f'    {e.strip()[:100]}')
        
        if dry_entries:
            print('  🛒 가상 진입 내역:')
            for e in dry_entries[:3]:
                 print(f'    {e.strip()[:100]}')
        print('-'*30)

if __name__ == "__main__":
    analyze_logs()
