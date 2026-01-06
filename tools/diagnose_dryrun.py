import os
import sys

def check_1_logs():
    log_path = r'C:\매매전략\logs\unified_bot.log'
    print('=== 로그 상태 ===')
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        print(f'총 줄 수: {len(lines)}')
        if lines:
            print('\n=== 최근 20줄 ===')
            for line in lines[-20:]:
                print(line.strip()[:100])
        else:
            print('로그가 비어있음')
        return "".join(lines)
    else:
        print('로그 파일 없음')
        return ""

def check_2_activity(content):
    if not content: return

    checks = {
        '웹소켓 연결': 'websocket' in content.lower() or 'connected' in content.lower(),
        '캔들 수신': 'candle' in content.lower() or 'kline' in content.lower(),
        '지표 계산': 'indicator' in content.lower() or 'rsi' in content.lower(),
        '시그널': 'signal' in content.lower() or 'pattern' in content.lower(),
        '에러': 'error' in content.lower() or 'exception' in content.lower()
    }
    
    print('\n=== 동작 체크 ===')
    for name, found in checks.items():
        status = '✅' if found else '❌'
        print(f'{name}: {status}')

def check_3_structure():
    filepath = r'C:\매매전략\core\unified_bot.py'
    print('\n=== 메인 루프 구조 ===')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        checks = {
            'run 메서드': 'def run(' in content,
            'start 메서드': 'def start(' in content,
            'while True': 'while True' in content or 'while self.is_running' in content,
            'websocket 콜백': 'on_message' in content or '_on_candle' in content,
            'sleep': 'sleep' in content
        }
        for name, found in checks.items():
            status = '✅' if found else '❌'
            print(f'{name}: {status}')
    else:
        print('core/unified_bot.py 파일 없음')

if __name__ == "__main__":
    content = check_1_logs()
    check_2_activity(content)
    check_3_structure()
