"""Phase 1 결과 검증

Phase 1 영향도 분석에서 찾은 최적값을
실제로 백테스트해서 검증

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()
df = dm.df_entry_full

# None 체크
if df is None:
    print("❌ 데이터 로드 실패")
    sys.exit(1)

# Phase 1 최적값
phase1_optimal = {
    'filter_tf': '2h',
    'trail_start_r': 0.4,
    'trail_dist_r': 0.02
}

print("=" * 60)
print("🔍 Phase 1 최적값 검증")
print("=" * 60)
print(f"\n최적 파라미터:")
for k, v in phase1_optimal.items():
    print(f"  {k}: {v}")

# 백테스트 실행
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')
trades = strategy.run_backtest(
    df_pattern=df,
    df_entry=df,
    **phase1_optimal
)

if isinstance(trades, tuple):
    trades = trades[0]

metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

print(f"\n결과:")
print(f"  거래수: {metrics['total_trades']}")
print(f"  승률: {metrics['win_rate']:.1f}%")
print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
print(f"  MDD: {metrics['mdd']:.1f}%")
print(f"  총 PnL: {metrics['total_pnl']:.1f}%")

print("\n" + "=" * 60)
print("📊 비교")
print("=" * 60)
print(f"Phase 1 예상: Sharpe ~21.5")
print(f"실제 결과: Sharpe {metrics['sharpe_ratio']:.2f}")
print(f"차이: {metrics['sharpe_ratio'] - 21.5:+.2f}")
