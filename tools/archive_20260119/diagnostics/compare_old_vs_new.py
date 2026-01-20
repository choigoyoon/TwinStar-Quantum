# -*- coding: utf-8 -*-
"""기존 vs 최적 파라미터 비교

목적: MDD 감소 확인 -> 레버리지 증가 가능성
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.parameters import DEFAULT_PARAMS
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.metrics import calculate_backtest_metrics


def run_backtest(params, label):
    """백테스트 실행 및 결과 반환"""
    print(f"\n{'='*60}")
    print(f"{label} 백테스트")
    print(f"{'='*60}")

    # 데이터 로드
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    dm.load_historical()

    if dm.df_entry_full is None:
        return None

    df = dm.df_entry_full

    # 백테스트
    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')
    trades = strategy.run_backtest(df_pattern=df, df_entry=df, **params)

    if isinstance(trades, tuple):
        trades = trades[0]

    # 메트릭
    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    print(f"거래수: {metrics['total_trades']:,}회")
    print(f"승률: {metrics['win_rate']:.1f}%")
    print(f"Sharpe: {metrics['sharpe_ratio']:.2f}")
    print(f"MDD: {metrics['mdd']:.2f}%")
    print(f"PF: {metrics['profit_factor']:.2f}")
    print(f"단리: {metrics['total_pnl']:.2f}%")

    return metrics


def main():
    print("="*60)
    print("기존 vs 최적 파라미터 비교")
    print("="*60)

    # 1. 기존 파라미터 (Baseline)
    old_params = DEFAULT_PARAMS.copy()
    old_params.update({
        'filter_tf': '4h',        # 기존
        'trail_start_r': 0.8,     # 기존
        'trail_dist_r': 0.1,      # 기존
        'atr_mult': 1.25,         # 기존
    })

    # 2. 최적 파라미터 (Phase 1 결과)
    new_params = DEFAULT_PARAMS.copy()
    new_params.update({
        'filter_tf': '2h',        # 최적
        'trail_start_r': 0.4,     # 최적
        'trail_dist_r': 0.02,     # 최적
        'atr_mult': 0.5,          # 최적
    })

    # 3. 백테스트 실행
    old_metrics = run_backtest(old_params, "1. 기존 방식")
    new_metrics = run_backtest(new_params, "2. 최적 방식")

    if old_metrics is None or new_metrics is None:
        print("백테스트 실패")
        return

    # 4. 비교 결과
    print(f"\n{'='*60}")
    print("비교 결과")
    print(f"{'='*60}")

    print(f"\n{'지표':<15} {'기존':>15} {'최적':>15} {'차이':>15}")
    print("-"*60)

    # MDD 비교 (중요!)
    mdd_diff = new_metrics['mdd'] - old_metrics['mdd']
    mdd_pct = (mdd_diff / old_metrics['mdd'] * 100) if old_metrics['mdd'] > 0 else 0
    print(f"{'MDD':<15} {old_metrics['mdd']:>14.2f}% {new_metrics['mdd']:>14.2f}% {mdd_diff:>+14.2f}% ({mdd_pct:+.1f}%)")

    # Sharpe 비교
    sharpe_diff = new_metrics['sharpe_ratio'] - old_metrics['sharpe_ratio']
    sharpe_pct = (sharpe_diff / old_metrics['sharpe_ratio'] * 100) if old_metrics['sharpe_ratio'] > 0 else 0
    print(f"{'Sharpe':<15} {old_metrics['sharpe_ratio']:>15.2f} {new_metrics['sharpe_ratio']:>15.2f} {sharpe_diff:>+14.2f} ({sharpe_pct:+.1f}%)")

    # 승률 비교
    wr_diff = new_metrics['win_rate'] - old_metrics['win_rate']
    print(f"{'승률':<15} {old_metrics['win_rate']:>14.1f}% {new_metrics['win_rate']:>14.1f}% {wr_diff:>+14.1f}%")

    # PF 비교
    pf_diff = new_metrics['profit_factor'] - old_metrics['profit_factor']
    print(f"{'PF':<15} {old_metrics['profit_factor']:>15.2f} {new_metrics['profit_factor']:>15.2f} {pf_diff:>+14.2f}")

    # 거래수 비교
    trades_diff = new_metrics['total_trades'] - old_metrics['total_trades']
    print(f"{'거래수':<15} {old_metrics['total_trades']:>14,}회 {new_metrics['total_trades']:>14,}회 {trades_diff:>+13,}회")

    # 5. 레버리지 권장
    print(f"\n{'='*60}")
    print("레버리지 권장")
    print(f"{'='*60}")

    # Kelly Criterion 간단 버전: f* = (승률 * PF - 1) / (PF - 1)
    old_kelly = 0
    new_kelly = 0

    if old_metrics['profit_factor'] > 1:
        old_kelly = (old_metrics['win_rate']/100 * old_metrics['profit_factor'] - 1) / (old_metrics['profit_factor'] - 1)

    if new_metrics['profit_factor'] > 1:
        new_kelly = (new_metrics['win_rate']/100 * new_metrics['profit_factor'] - 1) / (new_metrics['profit_factor'] - 1)

    # MDD 기반 안전 레버리지 (MDD 10% 이하 유지)
    old_safe_lev = 10.0 / old_metrics['mdd'] if old_metrics['mdd'] > 0 else 1
    new_safe_lev = 10.0 / new_metrics['mdd'] if new_metrics['mdd'] > 0 else 1

    print(f"\n기존 방식:")
    print(f"  MDD: {old_metrics['mdd']:.2f}%")
    print(f"  안전 레버리지 (MDD 10% 기준): {old_safe_lev:.1f}x")
    print(f"  Kelly 레버리지: {old_kelly*100:.1f}%")

    print(f"\n최적 방식:")
    print(f"  MDD: {new_metrics['mdd']:.2f}%")
    print(f"  안전 레버리지 (MDD 10% 기준): {new_safe_lev:.1f}x")
    print(f"  Kelly 레버리지: {new_kelly*100:.1f}%")

    lev_increase = new_safe_lev - old_safe_lev
    lev_increase_pct = (lev_increase / old_safe_lev * 100) if old_safe_lev > 0 else 0

    print(f"\n레버리지 증가 가능: {lev_increase:+.1f}x ({lev_increase_pct:+.1f}%)")

    # 6. 결론
    print(f"\n{'='*60}")
    print("결론")
    print(f"{'='*60}")

    if mdd_diff < 0:
        print(f"MDD가 {abs(mdd_diff):.2f}% 감소했습니다.")
        print(f"레버리지를 {new_safe_lev:.1f}x까지 안전하게 올릴 수 있습니다.")
        print(f"(기존 {old_safe_lev:.1f}x 대비 {lev_increase:+.1f}x 증가)")
    else:
        print(f"주의: MDD가 {mdd_diff:.2f}% 증가했습니다.")

    if sharpe_diff > 0:
        print(f"Sharpe가 {sharpe_diff:.2f} ({sharpe_pct:+.1f}%) 개선되었습니다.")

    print("\n완료!")


if __name__ == '__main__':
    main()
