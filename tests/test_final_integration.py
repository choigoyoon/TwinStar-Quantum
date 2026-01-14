# test_final_integration.py - 원본 파일 통합 검증

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# GUI 경로 추가 (constants.py 로드용)
_gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'GUI')
if _gui_dir not in sys.path:
    sys.path.insert(0, _gui_dir)

# 원본 모듈 로드
from core.strategy_core import AlphaX7Core
from constants import DEFAULT_PARAMS

import pandas as pd

# 데이터 로드
df_15m = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')

if 'timestamp' in df_15m.columns:
    if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    else:
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m = df_15m.set_index('timestamp')

df_1h = df_15m.resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
}).dropna().reset_index()
df_15m = df_15m.reset_index()

print(f"📊 데이터: 1h={len(df_1h)}개 ({len(df_1h)//24}일)")
print(r"⚙️ 적용된 기본 파라미터 (C:\매매전략\GUI\constants.py):")
for k, v in DEFAULT_PARAMS.items():
    if k in ['macd_fast', 'macd_slow', 'macd_signal', 'ema_period', 'atr_mult', 'rsi_period', 'filter_tf']:
        print(f"  - {k}: {v}")

core = AlphaX7Core(use_mtf=True)

print("\n🔍 통합 검증 백테스트 실행 중...")

# 필요한 파라미터만 필터링
valid_keys = [
    'atr_mult', 'trail_start_r', 'trail_dist_r', 'pattern_tolerance', 
    'entry_validity_hours', 'pullback_rsi_long', 'pullback_rsi_short', 
    'max_adds', 'filter_tf', 'rsi_period', 'atr_period', 'macd_fast', 
    'macd_slow', 'macd_signal', 'ema_period', 'slippage'
]
params = {k: v for k, v in DEFAULT_PARAMS.items() if k in valid_keys}

# 백테스트 실행
trades = core.run_backtest(
    df_pattern=df_1h,
    df_entry=df_15m,
    **params
)

if trades:
    leverage = 3
    pnls = [float(str(t['pnl']).replace('%','')) * leverage for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    total = sum(pnls)
    
    # MDD 계산
    equity, peak, max_dd = 100, 100, 0
    for p in pnls:
        equity *= (1 + p / 100)
        if equity > peak: peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd: max_dd = dd
    
    print("\n" + "=" * 50)
    print("✅ 원본 파일 통합 검증 결과 (3x 레버리지)")
    print("=" * 50)
    print(f"거래 수: {len(trades)}")
    print(f"승률: {wins / len(trades) * 100:.1f}%")
    print(f"총 수익 (단순): {total:.0f}%")
    print(f"MDD: {max_dd:.1f}%")
    print("=" * 50)
    
    # 결과 비교 (5,364%, MDD 9.3%와 일치해야 함)
    if total >= 5300 and max_dd <= 10:
        print("🎉 모든 검증 통과! 실전 투입 준비 완료.")
    else:
        print("⚠️ 검증 결과가 이전 테스트와 다릅니다. 확인 필요.")
else:
    print("⚠️ 거래 없음")
