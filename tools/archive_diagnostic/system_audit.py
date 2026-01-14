
from pathlib import Path
import json
import os
import sys
from datetime import datetime

# Fix encoding for Windows Terminal (Korean Support)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = Path(__file__).parent
# The user's script indicates these paths for production
cache = Path(r'C:\TwinStar Quantum\data\cache')
logs = Path(r'C:\TwinStar Quantum\logs')

print("=" * 70)
print("실제 시스템 상태 점검 (Real-world Audit)")
print("=" * 70)

# ============================================
# 1. 실제 파일 존재 확인
# ============================================
print("\n[1] 실제 파일 존재")
print("-" * 50)

files_to_check = {
    'bot_state.json': cache / 'bot_state.json',
    'Parquet 데이터': cache / 'bybit_btcusdt_15m.parquet',
    'trade_log.log': logs / 'trade_log.log',
    'bot_log.log': logs / 'bot_log.log',
}

for name, path in files_to_check.items():
    if path.exists():
        size = path.stat().st_size
        mtime = path.stat().st_mtime
        modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  ✅ {name}: {size:,} bytes (수정: {modified})")
    else:
        print(f"  ❌ {name}: 없음 ({path})")

# ============================================
# 2. bot_state.json 내용 확인
# ============================================
print("\n[2] bot_state.json 내용")
print("-" * 50)

state_file = cache / 'bot_state.json'
if state_file.exists():
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        print(f"  position: {state.get('position', 'N/A')}")
        print(f"  capital: {state.get('capital', 'N/A')}")
        print(f"  current_sl: {state.get('current_sl', 'N/A')}")
        
        # Check for order_id or order_ids (bt_state['positions'] has order_id)
        positions = state.get('positions', [])
        if positions:
            print(f"  positions: {len(positions)}개")
            for i, p in enumerate(positions[:3]):
                oid = p.get('order_id', 'None')
                print(f"    {i+1}. entry: {p.get('entry')}, ID: {oid}")
        else:
            print(f"  positions: 비어있음")
    except Exception as e:
        print(f"  ❌ 파싱 에러: {e}")
else:
    print(f"  ❌ 파일 없음")

# ============================================
# 3. trade_log.log 최근 내용
# ============================================
print("\n[3] trade_log.log 최근 기록")
print("-" * 50)

trade_log = logs / 'trade_log.log'
if trade_log.exists():
    try:
        with open(trade_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if lines:
            print(f"  총 {len(lines)}줄")
            print("  최근 3줄:")
            for line in lines[-3:]:
                print(f"    {line.strip()[:100]}")
        else:
            print("  ⚠️ 파일은 있지만 내용 없음")
    except Exception as e:
        print(f"  ❌ 읽기 에러: {e}")
else:
    print("  ❌ 파일 없음")

# ============================================
# 4. Parquet 데이터 상태
# ============================================
print("\n[4] Parquet 데이터 상태")
print("-" * 50)

parquet = cache / 'bybit_btcusdt_15m.parquet'
if parquet.exists():
    try:
        import pandas as pd
        df = pd.read_parquet(parquet)
        print(f"  행 수: {len(df):,}")
        if 'timestamp' in df.columns:
            print(f"  최신 시간: {df['timestamp'].max()}")
        if 'close' in df.columns:
            print(f"  최신 종가: {df['close'].iloc[-1]}")
    except ImportError:
        print("  ⚠️ pandas/pyarrow not available for deep check")
    except Exception as e:
        print(f"  ⚠️ 읽기 에러: {e}")
else:
    print("  ❌ 파일 없음")

# ============================================
# 5. 최근 로그 분석
# ============================================
print("\n[5] 최근 로그 분석")
print("-" * 50)

bot_log = logs / 'bot_log.log'
if bot_log.exists():
    try:
        with open(bot_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[-100:]
        
        status_checks = {
            'Bybit 연결': any('Bybit connected' in l for l in lines),
            'WebSocket 연결': any('[WS]' in l and 'Connected' in l for l in lines),
            'SYNC 수행': any('[SYNC]' in l for l in lines),
            '외부 포지션 감지': any('외부 포지션 감지' in l or 'EXTERNAL' in l.upper() for l in lines),
            '에러 발생': any('[ERROR]' in l or 'Critical' in l for l in lines),
        }
        
        for name, result in status_checks.items():
            print(f"  {'✅' if result else '❌'} {name}")
            
        errors = [l for l in lines if '[ERROR]' in l]
        if errors:
            print("\n  ⚠️ 최근 에러:")
            for e in errors[-2:]:
                print(f"    {e.strip()[:80]}")
    except Exception as e:
        print(f"  ❌ 분석 에러: {e}")
else:
    print("  ❌ 로그 파일 없음")

print("\n" + "=" * 70)
print("점검 완료")
print("=" * 70)
