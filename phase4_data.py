from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('💾 Phase 4: 데이터 처리 점검')
print('=' * 70)

#############################################
# [1] 데이터 관련 파일 구조
#############################################
print('\n📁 [1] 데이터 관련 파일')
print('-' * 70)

data_files = {
    'utils/data_manager.py': '데이터 매니저',
    'storage/trade_storage.py': '거래 저장소 (JSON)',
    'storage/trade_history.py': '거래 기록 (SQLite)',
    'core/unified_bot.py': '봇 엔진 (Parquet)',
    'exchanges/ws_handler.py': '웹소켓 핸들러',
}

for fpath, desc in data_files.items():
    f = base / fpath
    if f.exists():
        try:
            lines = len(f.read_text(encoding='utf-8', errors='ignore').split('\n'))
            print(f'  ✅ {fpath} ({desc}) - {lines:,}줄')
        except:
            print(f'  ✅ {fpath} ({desc})')
    else:
        print(f'  ❌ {fpath} ({desc}) - 없음')

#############################################
# [2] Parquet 저장/로드
#############################################
print('\n📊 [2] Parquet 저장/로드')
print('-' * 70)

parquet_features = {
    'pd.read_parquet': '로드',
    'to_parquet': '저장',
    'pyarrow': '엔진',
    'timestamp.*int64|int64.*timestamp': '타임스탬프 정규화',
    'backfill|백필': '백필링',
}

for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        found = []
        for feat, desc in parquet_features.items():
            if re.search(feat, code, re.I):
                found.append(desc)
        if found and 'parquet' in code.lower():
            print(f'  {f.relative_to(base)}: {", ".join(set(found))}')
    except:
        pass

#############################################
# [3] 캔들 데이터 처리
#############################################
print('\n🕯️ [3] 캔들 데이터 처리')
print('-' * 70)

bot_file = base / 'core' / 'unified_bot.py'
if bot_file.exists():
    code = bot_file.read_text(encoding='utf-8', errors='ignore')
    
    candle_features = {
        '_process_new_candle': '캔들 처리 함수',
        '_on_candle_close': '캔들 마감 핸들러',
        'df_entry': 'Entry 데이터프레임',
        'df_pattern': 'Pattern 데이터프레임',
        '_save_to_parquet': 'Parquet 저장',
        'backfill': '백필링',
    }
    
    for pattern, desc in candle_features.items():
        if pattern in code:
            # 라인 번호 찾기
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if pattern in line and ('def ' in line or '=' in line):
                    print(f'  ✅ {desc}: L{i+1}')
                    break
            else:
                print(f'  ✅ {desc}: 존재')
        else:
            print(f'  ❌ {desc}: 없음')

#############################################
# [4] 거래 저장소 (JSON + SQLite)
#############################################
print('\n💰 [4] 거래 저장소')
print('-' * 70)

# JSON Storage
json_storage = base / 'storage' / 'trade_storage.py'
if json_storage.exists():
    code = json_storage.read_text(encoding='utf-8', errors='ignore')
    json_features = ['add_trade', 'get_trades', 'save', 'load', 'json']
    found = [f for f in json_features if f in code.lower()]
    print(f'  JSON Storage: {", ".join(found)}')

# SQLite Storage
sqlite_storage = base / 'storage' / 'trade_history.py'
if sqlite_storage.exists():
    code = sqlite_storage.read_text(encoding='utf-8', errors='ignore')
    sqlite_features = ['sqlite', 'INSERT', 'SELECT', 'CREATE TABLE', 'connect']
    found = [f for f in sqlite_features if f in code]
    print(f'  SQLite Storage: {", ".join(found)}')

#############################################
# [5] 시간 동기화
#############################################
print('\n⏰ [5] 시간 동기화')
print('-' * 70)

time_features = {
    'sync_time|time.*sync': '시간 동기화 함수',
    'offset': '오프셋 적용',
    'fetchTime|get_server_time': '서버 시간 조회',
    'latency': '레이턴시 계산',
}

for f in [base / 'core' / 'unified_bot.py', base / 'exchanges' / 'ws_handler.py']:
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        found = []
        for pattern, desc in time_features.items():
            if re.search(pattern, code, re.I):
                found.append(desc)
        if found:
            print(f'  {f.name}: {", ".join(found)}')

#############################################
# [6] 웹소켓 데이터 흐름
#############################################
print('\n🔌 [6] 웹소켓 데이터 흐름')
print('-' * 70)

ws_file = base / 'exchanges' / 'ws_handler.py'
if ws_file.exists():
    code = ws_file.read_text(encoding='utf-8', errors='ignore')
    
    ws_features = {
        'connect': '연결',
        'on_message': '메시지 수신',
        'on_close': '연결 종료',
        'reconnect': '재연결',
        'ping|pong': '핑퐁',
        'subscribe': '구독',
        'kline|candle': '캔들 스트림',
    }
    
    for pattern, desc in ws_features.items():
        if re.search(pattern, code, re.I):
            print(f'  ✅ {desc}')
        else:
            print(f'  ❌ {desc}')

#############################################
# [7] 데이터 무결성 체크
#############################################
print('\n🔒 [7] 데이터 무결성')
print('-' * 70)

integrity_patterns = {
    'duplicate': '중복 제거',
    'dropna|fillna': 'NaN 처리',
    'sort_values|sort_index': '정렬',
    'reset_index': '인덱스 리셋',
    'astype.*int64': '타입 변환',
}

bot_file = base / 'core' / 'unified_bot.py'
if bot_file.exists():
    code = bot_file.read_text(encoding='utf-8', errors='ignore')
    for pattern, desc in integrity_patterns.items():
        if re.search(pattern, code, re.I):
            print(f'  ✅ {desc}')
        else:
            print(f'  ⚠️ {desc}: 확인 필요')

print('\n' + '=' * 70)
