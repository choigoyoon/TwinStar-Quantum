"""
올바른 파라미터로 시장가 vs 지정가 비교

JSON 데이터의 최적 파라미터 사용:
- atr_mult: 1.25
- filter_tf: 4h (12h 아님!)
- trail_start_r: 0.4 (0.8 아님!)
- trail_dist_r: 0.05 (0.015 아님!)
- 예상 승률: 95.71%
- 예상 거래: 2,192개
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics

# 올바른 파라미터 (JSON에서 추출)
CORRECT_PARAMS = {
    'atr_mult': 1.25,
    'filter_tf': '4h',  # 프리셋 파일은 12h였지만 실제 최고는 4h!
    'trail_start_r': 0.4,
    'trail_dist_r': 0.05,
    'entry_validity_hours': 6.0,
    'leverage': 1,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7
}

print(f"\n{'='*80}")
print(f"올바른 파라미터로 시장가 백테스트")
print(f"{'='*80}")
print(f"파라미터: {CORRECT_PARAMS}")
print(f"{'='*80}\n")

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()

if dm.df_entry_full is None:
    raise ValueError("데이터가 비어 있습니다. load_historical() 실패")

df_15m = dm.df_entry_full.copy()

# 리샘플링
df_temp = df_15m.set_index('timestamp')
df_1h = df_temp.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()
df_1h.reset_index(inplace=True)

# 지표 추가
add_all_indicators(df_1h, inplace=True)

print(f"데이터: {len(df_1h):,}개 봉\n")

# 전략 초기화
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

# 시장가 백테스트
print("시장가 백테스트 실행 중...\n")

trades = strategy.run_backtest(
    df_pattern=df_1h,
    df_entry=df_1h,
    slippage=0.001,
    **CORRECT_PARAMS
)

print(f"총 거래: {len(trades):,}개\n")

# 메트릭 계산
metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

# 결과 출력
print(f"{'='*80}")
print(f"시장가 백테스트 결과")
print(f"{'='*80}")
print(f"총 거래:       {metrics['total_trades']:,}회")
print(f"승률:          {metrics['win_rate']:.2f}%")
print(f"거래당 PnL:    {metrics['avg_pnl']:.3f}%")
print(f"총 PnL:        {metrics['total_pnl']:.2f}%")
print(f"MDD:           {metrics['mdd']:.2f}%")
print(f"Sharpe Ratio:  {metrics['sharpe_ratio']:.2f}")
print(f"Profit Factor: {metrics['profit_factor']:.2f}")
print(f"{'='*80}\n")

# JSON 데이터와 비교
print(f"{'='*80}")
print(f"JSON 데이터와 비교")
print(f"{'='*80}")
print(f"{'지표':<15} {'JSON':>12} {'백테스트':>12} {'차이':>12}")
print(f"{'-'*80}")
print(f"{'승률':<15} {95.71:>11.2f}% {metrics['win_rate']:>11.2f}% {metrics['win_rate']-95.71:>11.2f}%p")
print(f"{'거래 횟수':<15} {2192:>12,} {metrics['total_trades']:>12,} {metrics['total_trades']-2192:>12,}")
print(f"{'Sharpe':<15} {27.32:>12.2f} {metrics['sharpe_ratio']:>12.2f} {metrics['sharpe_ratio']-27.32:>12.2f}")
print(f"{'MDD':<15} {0.84:>11.2f}% {metrics['mdd']:>11.2f}% {metrics['mdd']-0.84:>11.2f}%")
print(f"{'='*80}\n")

if abs(metrics['win_rate'] - 95.71) < 1.0 and abs(metrics['total_trades'] - 2192) < 50:
    print("OK: JSON 데이터와 일치합니다!")
    print("\n이제 이 거래들을 지정가로 재시뮬레이션합니다...")
else:
    print("WARNING: JSON 데이터와 차이가 있습니다.")
    print("프리셋 파일이 아닌 올바른 파라미터를 사용했는지 확인하세요.")
