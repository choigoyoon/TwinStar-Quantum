import os
import glob
import subprocess

def find_latest_log():
    log_dir = r'C:\매매전략\logs'
    # Check both specific and generic names just in case
    candidates = glob.glob(os.path.join(log_dir, 'bot_*.log')) + glob.glob(os.path.join(log_dir, 'unified_bot.log'))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)

def check_status():
    log_path = find_latest_log()
    
    if log_path:
        print(f"📂 Found Log File: {log_path}")
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
        print('\n=== 최근 30줄 ===')
        for line in lines[-30:]:
            print(line.strip()[:100])
            
        print('\n=== 동작 상태 검사 ===')
        print(f'총 로그: {len(lines)}줄')
        
        checks = {
            '웹소켓 연결': content.count('Connected') + content.count('connected'), # Case insensitive-ish
            '캔들 수신': content.count('candle') + content.count('Candle') + content.lower().count('kline'),
            '지표 계산': content.count('indicator') + content.count('RSI') + content.count('ATR'),
            '시그널 감지': content.count('signal') + content.count('Signal') + content.count('pattern'),
            '에러': content.lower().count('error'),
            '경고': content.lower().count('warning')
        }
        
        for name, count in checks.items():
            # Logic from user request
            if name == '에러':
                status = '⚠️' if count > 0 else '✅'
            else:
                status = '✅' if count > 0 else '❌'
            print(f'{name}: {count}회 {status}')
            
        recent_errors = [l for l in lines[-100:] if 'error' in l.lower()]
        if recent_errors:
            print(f'\n=== 최근 에러 ({len(recent_errors)}개) ===')
            for e in recent_errors[-5:]:
                print(f'  {e.strip()[:80]}')
        else:
            print('\n✅ 최근 100줄 에러 없음')
            
    else:
        print("❌ 로그 파일을 찾을 수 없습니다.")

def check_process():
    print('\n=== 프로세스 확인 ===')
    try:
        result = subprocess.check_output('tasklist | findstr python', shell=True).decode('utf-8', errors='ignore')
        print(result.strip())
    except subprocess.CalledProcessError:
        print("Python 프로세스가 발견되지 않았습니다.")

if __name__ == "__main__":
    check_status()
    check_process()
