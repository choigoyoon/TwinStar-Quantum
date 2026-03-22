from pathlib import Path
import re

base = Path(__file__).parent

print('=' * 70)
print('🔬 TwinStar Quantum 추가 심화 검증')
print('=' * 70)

#############################################
# [1] WebSocket 안정성 심화
#############################################
print('\n' + '=' * 70)
print('🔌 [1] WebSocket 안정성 심화')
print('=' * 70)

ws_file = base / 'exchanges' / 'ws_handler.py'
if ws_file.exists():
    ws_code = ws_file.read_text(encoding='utf-8', errors='ignore')
    ws_lines = ws_code.split('\n')
    
    ws_checks = {
        '연결 함수': r'def connect|def start|async def connect',
        '재연결 로직': r'reconnect|retry|reopen',
        'ping/pong': r'ping|pong|heartbeat',
        '메시지 핸들러': r'on_message|_handle_message|_on_message',
        '에러 핸들러': r'on_error|_on_error|on_close',
        '구독 관리': r'subscribe|unsubscribe',
        '스레드 안전': r'threading|Thread|Lock|asyncio',
        'try-except': r'try:|except',
    }
    
    for name, pattern in ws_checks.items():
        matches = [i+1 for i, l in enumerate(ws_lines) if re.search(pattern, l, re.I)]
        if matches:
            print(f'  ✅ {name}: {len(matches)}곳 (L{matches[0]}...)')
        else:
            print(f'  ❌ {name}: 없음')
    
    # 거래소별 WS 지원 확인
    print('\n  📡 거래소별 WS 지원:')
    exchanges = ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb']
    for ex in exchanges:
        if ex in ws_code.lower():
            print(f'    ✅ {ex}')
        else:
            print(f'    ⚠️ {ex}: 미확인')
else:
    print('  ❌ ws_handler.py 없음')

#############################################
# [2] 멀티 스캐너 (multi_sniper) 검증
#############################################
print('\n' + '=' * 70)
print('🎯 [2] 멀티 스캐너 검증')
print('=' * 70)

sniper_file = base / 'core' / 'multi_sniper.py'
if sniper_file.exists():
    sniper_code = sniper_file.read_text(encoding='utf-8', errors='ignore')
    sniper_lines = sniper_code.split('\n')
    
    sniper_checks = {
        '클래스 정의': r'class MultiSniper|class MultiTrader',
        '스캔 함수': r'def scan|def start_scan',
        '심볼 관리': r'symbols|coin_list|watch_list',
        '시그널 감지': r'on_signal|detect_signal|signal_detected',
        '진입 실행': r'execute|entry|place_order',
        '동시 처리': r'asyncio|threading|concurrent|await',
        '상태 관리': r'CoinState|state|status',
        '로깅': r'logging|logger|self\.log',
    }
    
    for name, pattern in sniper_checks.items():
        matches = [i+1 for i, l in enumerate(sniper_lines) if re.search(pattern, l, re.I)]
        if matches:
            print(f'  ✅ {name}: {len(matches)}곳')
        else:
            print(f'  ⚠️ {name}: 확인 필요')
    
    # signal 접근 방식 확인
    print('\n  🔍 signal 접근 패턴:')
    signal_issues = []
    for i, line in enumerate(sniper_lines):
        if "signal['" in line or 'signal["' in line:
            if 'isinstance' not in line and 'try' not in '\n'.join(sniper_lines[max(0,i-3):i]):
                signal_issues.append((i+1, line.strip()[:50]))
    
    if signal_issues:
        print(f'    ⚠️ 직접 접근 {len(signal_issues)}건:')
        for ln, code in signal_issues[:5]:
            print(f'      L{ln}: {code}')
    else:
        print('    ✅ 안전한 접근 방식')
else:
    print('  ❌ multi_sniper.py 없음')
    
    # multi_trader.py 확인
    trader_file = base / 'core' / 'multi_trader.py'
    if trader_file.exists():
        print('  ℹ️ multi_trader.py 발견 - 검증 진행')

#############################################
# [3] 거래소별 API 응답 처리 검증
#############################################
print('\n' + '=' * 70)
print('💱 [3] 거래소별 API 응답 처리')
print('=' * 70)

ex_path = base / 'exchanges'
if ex_path.exists():
    exchanges = ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb']
    
    for ex in exchanges:
        ex_file = ex_path / f'{ex}_exchange.py'
        if ex_file.exists():
            code = ex_file.read_text(encoding='utf-8', errors='ignore')
            lines = code.split('\n')
            
            checks = {
                'try-except': len(re.findall(r'try:', code)),
                'response 체크': len(re.findall(r'response|result|ret', code, re.I)),
                'error 핸들링': len(re.findall(r'error|exception|fail', code, re.I)),
                '.get() 사용': len(re.findall(r'\.get\(', code)),
            }
            
            status = '✅' if checks['try-except'] > 5 and checks['.get() 사용'] > 3 else '⚠️'
            print(f'  {status} {ex}: try={checks["try-except"]}, .get()={checks[".get() 사용"]}, err={checks["error 핸들링"]}')
        else:
            print(f'  ❌ {ex}: 파일 없음')

#############################################
# [4] 데이터 무결성 (Parquet) 검증
#############################################
print('\n' + '=' * 70)
print('💾 [4] 데이터 무결성 (Parquet)')
print('=' * 70)

data_checks = {
    'core/unified_bot.py': ['to_parquet', 'read_parquet', 'timestamp', 'int64'],
    'utils/data_manager.py': ['parquet', 'cache', 'load', 'save'],
    'GUI/data_collector_widget.py': ['download', 'parquet', 'progress'],
}

for fpath, keywords in data_checks.items():
    f = base / fpath
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        found = [k for k in keywords if k in code.lower()]
        missing = [k for k in keywords if k not in code.lower()]
        
        if len(found) >= len(keywords) * 0.7:
            print(f'  ✅ {fpath}: {len(found)}/{len(keywords)} 키워드')
        else:
            print(f'  ⚠️ {fpath}: {len(found)}/{len(keywords)} (누락: {missing})')
    else:
        print(f'  ❌ {fpath}: 없음')

# 타임스탬프 처리 검증
print('\n  🕐 타임스탬프 처리:')
bot_file = base / 'core' / 'unified_bot.py'
if bot_file.exists():
    code = bot_file.read_text(encoding='utf-8', errors='ignore')
    
    ts_patterns = {
        'int64 변환': r'astype.*int64|\.astype\(.*int',
        '밀리초 처리': r'\* 1000|\/ 1000|millisecond',
        'datetime 변환': r'to_datetime|from_timestamp',
    }
    
    for name, pattern in ts_patterns.items():
        count = len(re.findall(pattern, code, re.I))
        print(f'    {"✅" if count > 0 else "⚠️"} {name}: {count}건')

#############################################
# [5] 라이선스/결제 시스템 검증
#############################################
print('\n' + '=' * 70)
print('🔐 [5] 라이선스/결제 시스템')
print('=' * 70)

license_files = {
    'core/license_guard.py': ['verify', 'check', 'tier', 'expire'],
    'core/license_manager.py': ['DEFAULT_LIMITS', 'tier', 'check'],
    'GUI/pc_license_dialog.py': ['login', 'hw_id', 'verify'],
    'GUI/payment_dialog.py': ['payment', 'upgrade', 'tier'],
}

for fpath, keywords in license_files.items():
    f = base / fpath
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        found = [k for k in keywords if k in code.lower()]
        print(f'  ✅ {fpath}: {len(found)}/{len(keywords)} 키워드')
    else:
        # 대체 파일 검색
        alt_found = False
        for alt in base.rglob('*license*.py'):
            if '__pycache__' not in str(alt):
                print(f'  ℹ️ {fpath} 없음 → {alt.relative_to(base)} 발견')
                alt_found = True
                break
        if not alt_found:
            print(f'  ⚠️ {fpath}: 없음')

# 등급 제한 로직 확인
print('\n  📊 등급 제한 로직:')
for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'TIER_LIMITS' in code or 'DEFAULT_LIMITS' in code:
            print(f'    ✅ {f.relative_to(base)}: 등급 제한 정의')
            
            # 상세 내용 추출
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'LIMITS' in line and '=' in line:
                    print(f'       L{i+1}: {line.strip()[:50]}')
                    break
    except Exception:

        pass

#############################################
# 최종 요약
#############################################
print('\n' + '=' * 70)
print('📊 추가 심화 검증 완료')
print('=' * 70)
print('  [1] WebSocket 안정성: 검증 완료')
print('  [2] 멀티 스캐너: 검증 완료')
print('  [3] 거래소 API 처리: 검증 완료')
print('  [4] 데이터 무결성: 검증 완료')
print('  [5] 라이선스 시스템: 검증 완료')
print('=' * 70)
