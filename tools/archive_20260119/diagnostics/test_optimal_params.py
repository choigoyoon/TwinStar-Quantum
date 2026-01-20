"""최적 파라미터 백테스트 (Phase 1 결과 검증)

영향도 분석 결과:
1. filter_tf: +4.01 영향 → 최적값 2h
2. trail_start_r: +3.51 영향 → 최적값 0.4
3. trail_dist_r: +2.47 영향 → 최적값 0.02
4. atr_mult: +1.15 영향 → 최적값 0.5

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.parameters import DEFAULT_PARAMS
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics


def run_optimal_backtest():
    """최적 파라미터로 백테스트 실행"""
    print("=" * 60)
    print("🎯 최적 파라미터 백테스트 (Phase 1 결과)")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n📥 데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 없음.")
            return

        df = dm.df_entry_full
        print(f"✅ 데이터 로드 완료: {len(df)}개 캔들")

    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    # 2. 파라미터 설정
    # Baseline (기본값)
    baseline_params = DEFAULT_PARAMS.copy()

    # Optimal (Phase 1 결과)
    optimal_params = DEFAULT_PARAMS.copy()
    optimal_params.update({
        'filter_tf': '2h',           # 영향도 +4.01
        'trail_start_r': 0.4,        # 영향도 +3.51
        'trail_dist_r': 0.02,        # 영향도 +2.47
        'atr_mult': 0.5,             # 영향도 +1.15
        'entry_validity_hours': 6    # 영향도 +0.12 (기본값 유지)
    })

    print(f"\n{'='*60}")
    print(f"파라미터 비교")
    print(f"{'='*60}")
    print(f"{'파라미터':<20} {'Baseline':>15} {'Optimal':>15}")
    print(f"{'-'*60}")
    print(f"{'filter_tf':<20} {baseline_params['filter_tf']:>15} {optimal_params['filter_tf']:>15}")
    print(f"{'trail_start_r':<20} {baseline_params['trail_start_r']:>15.2f} {optimal_params['trail_start_r']:>15.2f}")
    print(f"{'trail_dist_r':<20} {baseline_params['trail_dist_r']:>15.2f} {optimal_params['trail_dist_r']:>15.2f}")
    print(f"{'atr_mult':<20} {baseline_params['atr_mult']:>15.2f} {optimal_params['atr_mult']:>15.2f}")
    print(f"{'entry_validity':<20} {baseline_params.get('entry_validity_hours', 6):>15.0f}h {optimal_params['entry_validity_hours']:>15.0f}h")

    # 3. Baseline 백테스트
    print(f"\n{'='*60}")
    print(f"1️⃣ Baseline 백테스트")
    print(f"{'='*60}")

    strategy_baseline = AlphaX7Core(use_mtf=True, strategy_type='macd')
    start_time = datetime.now()

    trades_baseline = strategy_baseline.run_backtest(
        df_pattern=df,
        df_entry=df,
        **baseline_params
    )

    elapsed_baseline = (datetime.now() - start_time).total_seconds()

    if isinstance(trades_baseline, tuple):
        trades_baseline = trades_baseline[0]

    metrics_baseline = calculate_backtest_metrics(
        trades_baseline,
        leverage=1,
        capital=100.0
    )

    print(f"\n거래수: {metrics_baseline['total_trades']:,}회")
    print(f"승률: {metrics_baseline['win_rate']:.1f}%")
    print(f"Sharpe: {metrics_baseline['sharpe_ratio']:.2f}")
    print(f"MDD: {metrics_baseline['mdd']:.2f}%")
    print(f"PF: {metrics_baseline['profit_factor']:.2f}")
    print(f"단리: {metrics_baseline['total_pnl']:.2f}%")
    print(f"소요시간: {elapsed_baseline:.1f}초")

    # 4. Optimal 백테스트
    print(f"\n{'='*60}")
    print(f"2️⃣ Optimal 백테스트")
    print(f"{'='*60}")

    strategy_optimal = AlphaX7Core(use_mtf=True, strategy_type='macd')
    start_time = datetime.now()

    trades_optimal = strategy_optimal.run_backtest(
        df_pattern=df,
        df_entry=df,
        **optimal_params
    )

    elapsed_optimal = (datetime.now() - start_time).total_seconds()

    if isinstance(trades_optimal, tuple):
        trades_optimal = trades_optimal[0]

    metrics_optimal = calculate_backtest_metrics(
        trades_optimal,
        leverage=1,
        capital=100.0
    )

    print(f"\n거래수: {metrics_optimal['total_trades']:,}회")
    print(f"승률: {metrics_optimal['win_rate']:.1f}%")
    print(f"Sharpe: {metrics_optimal['sharpe_ratio']:.2f}")
    print(f"MDD: {metrics_optimal['mdd']:.2f}%")
    print(f"PF: {metrics_optimal['profit_factor']:.2f}")
    print(f"단리: {metrics_optimal['total_pnl']:.2f}%")
    print(f"소요시간: {elapsed_optimal:.1f}초")

    # 5. 비교 결과
    print(f"\n{'='*60}")
    print(f"📊 성과 비교")
    print(f"{'='*60}")

    sharpe_diff = metrics_optimal['sharpe_ratio'] - metrics_baseline['sharpe_ratio']
    sharpe_pct = (sharpe_diff / metrics_baseline['sharpe_ratio'] * 100) if metrics_baseline['sharpe_ratio'] > 0 else 0

    wr_diff = metrics_optimal['win_rate'] - metrics_baseline['win_rate']
    mdd_diff = metrics_optimal['mdd'] - metrics_baseline['mdd']
    pf_diff = metrics_optimal['profit_factor'] - metrics_baseline['profit_factor']
    pf_pct = (pf_diff / metrics_baseline['profit_factor'] * 100) if metrics_baseline['profit_factor'] > 0 else 0

    print(f"{'지표':<15} {'Baseline':>15} {'Optimal':>15} {'차이':>15}")
    print(f"{'-'*60}")
    print(f"{'Sharpe':<15} {metrics_baseline['sharpe_ratio']:>15.2f} {metrics_optimal['sharpe_ratio']:>15.2f} {sharpe_diff:>+14.2f} ({sharpe_pct:+.1f}%)")
    print(f"{'승률':<15} {metrics_baseline['win_rate']:>14.1f}% {metrics_optimal['win_rate']:>14.1f}% {wr_diff:>+14.1f}%")
    print(f"{'MDD':<15} {metrics_baseline['mdd']:>14.2f}% {metrics_optimal['mdd']:>14.2f}% {mdd_diff:>+14.2f}%")
    print(f"{'PF':<15} {metrics_baseline['profit_factor']:>15.2f} {metrics_optimal['profit_factor']:>15.2f} {pf_diff:>+14.2f} ({pf_pct:+.1f}%)")
    print(f"{'거래수':<15} {metrics_baseline['total_trades']:>14,}회 {metrics_optimal['total_trades']:>14,}회 {metrics_optimal['total_trades']-metrics_baseline['total_trades']:>+13,}회")

    # 6. 결론
    print(f"\n{'='*60}")
    print(f"🎯 결론")
    print(f"{'='*60}")

    if sharpe_diff > 0:
        print(f"✅ 최적 파라미터가 Baseline 대비 Sharpe {sharpe_pct:+.1f}% 개선")
        print(f"   → 영향도 분석 결과가 유효함을 확인!")
    else:
        print(f"⚠️ 최적 파라미터가 Baseline 대비 Sharpe {sharpe_pct:+.1f}% 하락")
        print(f"   → 영향도 분석 재검토 필요")

    # 7. 다음 단계 제안
    print(f"\n{'='*60}")
    print(f"💡 다음 단계")
    print(f"{'='*60}")
    print(f"1. Fine-Tuning: tools/test_fine_tuning.py 실행 (1,089개 조합 정밀 탐색)")
    print(f"2. 프리셋 생성: 최적 파라미터를 JSON으로 저장")
    print(f"3. Walk-Forward 검증: 시간대별 안정성 확인")

    print(f"\n✅ 테스트 완료!")


if __name__ == '__main__':
    run_optimal_backtest()
