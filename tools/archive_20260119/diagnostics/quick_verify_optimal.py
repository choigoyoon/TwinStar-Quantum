# -*- coding: utf-8 -*-
"""최적 프리셋 빠른 검증 (Phase 1)

이모지 없이 안전하게 실행
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics


def main():
    print("="*60)
    print("Phase 1 최적 프리셋 검증")
    print("="*60)

    # 1. 프리셋 로드
    preset_path = 'presets/bybit_BTCUSDT_1h_optimal_phase1.json'
    with open(preset_path, 'r', encoding='utf-8') as f:
        preset = json.load(f)

    params = preset['best_params']

    print("\n최적 파라미터:")
    print(f"  filter_tf: {params['filter_tf']}")
    print(f"  trail_start_r: {params['trail_start_r']}")
    print(f"  trail_dist_r: {params['trail_dist_r']}")
    print(f"  atr_mult: {params['atr_mult']}")

    # 2. 데이터 로드
    print("\n데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    dm.load_historical()

    if dm.df_entry_full is None or len(dm.df_entry_full) == 0:
        print("데이터 없음")
        return

    df = dm.df_entry_full
    print(f"데이터: {len(df):,}개 캔들")

    # 3. 백테스트 실행
    print("\n백테스트 실행 중...")
    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

    trades = strategy.run_backtest(
        df_pattern=df,
        df_entry=df,
        **params
    )

    if isinstance(trades, tuple):
        trades = trades[0]

    # 4. 메트릭 계산
    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # 5. 결과 출력
    print("\n"+"="*60)
    print("백테스트 결과")
    print("="*60)
    print(f"총 거래: {metrics['total_trades']:,}회")
    print(f"승률: {metrics['win_rate']:.1f}%")
    print(f"Sharpe: {metrics['sharpe_ratio']:.2f}")
    print(f"MDD: {metrics['mdd']:.2f}%")
    print(f"PF: {metrics['profit_factor']:.2f}")
    print(f"단리: {metrics['total_pnl']:.2f}%")

    # 6. 예상값과 비교
    expected_sharpe = preset['meta_info']['optimal_sharpe']
    actual_sharpe = metrics['sharpe_ratio']
    diff = actual_sharpe - expected_sharpe

    print("\n"+"="*60)
    print("예상 vs 실제")
    print("="*60)
    print(f"예상 Sharpe: {expected_sharpe:.2f}")
    print(f"실제 Sharpe: {actual_sharpe:.2f}")
    print(f"차이: {diff:+.2f}")

    if abs(diff) < 1.0:
        print("\n결과: 예상값과 일치 (오차 <1.0)")
    else:
        print(f"\n주의: 예상값과 차이 발생 (오차 {abs(diff):.2f})")

    print("\n완료!")


if __name__ == '__main__':
    main()
