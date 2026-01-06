"""15분봉 리샘플링 + 백테스트 테스트"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')
import pandas as pd

# 데이터 로드
df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
print(f'15m 데이터: {len(df):,} 캔들')
print(f'컬럼: {list(df.columns)}')

# timestamp 타입 확인
if 'timestamp' in df.columns:
    print(f'timestamp dtype: {df["timestamp"].dtype}')
    print(f'첫 timestamp: {df["timestamp"].iloc[0]}')

# timestamp 변환 및 리샘플링
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df = df.set_index('timestamp')

df_1h = df.resample('1h').agg({
    'open': 'first', 
    'high': 'max', 
    'low': 'min', 
    'close': 'last', 
    'volume': 'sum'
}).dropna().reset_index()

print(f'1H 데이터: {len(df_1h):,} 캔들')
print(f'1H 컬럼: {list(df_1h.columns)}')

# 백테스트 테스트
from core.strategy_core import AlphaX7Core
core = AlphaX7Core(use_mtf=False)

# 최근 2000개만 테스트
test_df = df_1h.tail(2000)
trades = core.run_backtest(df_pattern=test_df, df_entry=test_df)

print(f'\n거래 수: {len(trades) if trades else 0}')
if trades and len(trades) > 0:
    print(f'첫 거래: {trades[0]}')
    pnl_sum = sum(t.get('pnl', 0) for t in trades)
    wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
    print(f'총 수익: {pnl_sum:.2f}%')
    print(f'승률: {wins/len(trades)*100:.1f}%')
else:
    print('거래 없음 - 패턴 감지 실패')
