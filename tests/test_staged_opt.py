"""최적화 결과 테스트"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

import pandas as pd
from core.optimization_logic import OptimizationEngine

# 데이터 로드 + 리샘플링
df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
print(f'원본 데이터: {len(df):,} 캔들 (15m)')

df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df = df.set_index('timestamp')
df_1h = df.resample('1h').agg({
    'open': 'first', 
    'high': 'max', 
    'low': 'min', 
    'close': 'last', 
    'volume': 'sum'
}).dropna().reset_index()
print(f'리샘플링: {len(df_1h):,} 캔들 (1H)')

# 순차 최적화 실행
print('\n=== 순차 최적화 시작 ===')
engine = OptimizationEngine()

def callback(stage, msg, params):
    print(f'  {stage}단계: {msg}')

result = engine.run_staged_optimization(
    df=df_1h,
    target_mdd=20.0,
    max_workers=4,
    stage_callback=callback
)

# 결과 출력
print('\n' + '='*50)
print('            최적화 결과')
print('='*50)
total = result.get('total_combinations', 0)
mdd = result.get('mdd', 0)
lev = result.get('leverage', 1)
print(f'총 조합 테스트: {total}개')
print(f'MDD: {mdd:.2f}%')
print(f'적정 레버리지: {lev}x')

r = result.get('final_result')
if r:
    print(f'\n📊 최종 성과:')
    print(f'  승률: {r.win_rate:.1f}%')
    print(f'  수익률: {r.simple_return:.1f}%')
    print(f'  복리수익: {r.compound_return:.1f}%')
    print(f'  거래수: {r.trade_count}')
    print(f'  Sharpe: {r.sharpe_ratio:.2f}')
    print(f'  MDD: {r.max_drawdown:.1f}%')

print('\n✅ 최적 파라미터:')
params = result.get('params', {})
keys = ['filter_tf', 'atr_mult', 'trail_start_r', 'trail_dist_r', 
        'direction', 'pullback_rsi_long', 'pullback_rsi_short', 'leverage']
for k in keys:
    if k in params:
        print(f'  {k}: {params[k]}')
        
print('\n🎉 완료!')
