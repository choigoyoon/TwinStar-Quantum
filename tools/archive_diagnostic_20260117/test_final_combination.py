#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
최종 조합 테스트

Phase 5 최적 파라미터 + leverage 조정
- trail_start_r=1.0, entry_valid=6h, trail_dist=0.02
- leverage: [1, 2, 3]

목표: 승률 80%+, MDD 20% 이하
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime

from config.parameters import DEFAULT_PARAMS
from core.optimizer import BacktestOptimizer
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core

def test_final_combination():
    """최종 조합 테스트"""

    print("=" * 80)
    print("최종 조합 테스트 - 승률 80%+, MDD 20% 목표")
    print("=" * 80)
    print()

    # 1. 데이터 로드
    print("데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT')
    if not dm.load_historical():
        print("데이터 로드 실패")
        return

    df = dm.df_entry_full
    if df is None or df.empty:
        print("데이터가 비어있습니다")
        return

    total_days = (df['timestamp'].max() - df['timestamp'].min()).days
    print(f"데이터: {len(df):,}개 캔들 ({total_days}일)")
    print()

    # 2. 테스트 조합
    print("테스트 조합:")
    print("-" * 80)

    # Phase 5 최적 파라미터
    phase5_params = {
        'filter_tf': '4h',
        'atr_mult': 1.5,
        'trail_start_r': 1.0,
        'entry_validity_hours': 6.0,
        'trail_dist_r': 0.02,
    }

    # DEFAULT_PARAMS 최적 파라미터
    default_params = {
        'filter_tf': '4h',
        'atr_mult': 1.25,
        'trail_start_r': 0.8,
        'entry_validity_hours': 6.0,
        'trail_dist_r': 0.1,
    }

    test_configs = [
        ("Phase5 최적 (1x)", phase5_params, 1),
        ("Phase5 최적 (2x)", phase5_params, 2),
        ("Phase5 최적 (3x)", phase5_params, 3),
        ("DEFAULT_PARAMS (1x)", default_params, 1),
        ("DEFAULT_PARAMS (2x)", default_params, 2),
    ]

    for name, custom_params, leverage in test_configs:
        print(f"{name}:")
        print(f"  - filter_tf: {custom_params['filter_tf']}")
        print(f"  - atr_mult: {custom_params['atr_mult']}")
        print(f"  - trail_start_r: {custom_params['trail_start_r']}")
        print(f"  - trail_dist_r: {custom_params['trail_dist_r']}")
        print(f"  - entry_validity: {custom_params['entry_validity_hours']}h")
        print(f"  - leverage: {leverage}x")
        print()

    # 3. Optimizer 초기화
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df
    )

    # 4. 백테스트 실행
    results = []

    print("백테스트 실행 중...")
    print("=" * 80)
    print()

    for idx, (name, custom_params, leverage) in enumerate(test_configs, 1):
        print(f"[{idx}/{len(test_configs)}] {name}")

        # 파라미터 병합
        params = DEFAULT_PARAMS.copy()
        params.update(custom_params)
        params['leverage'] = leverage
        params['max_mdd'] = 100.0

        try:
            result = optimizer._run_single(
                params,
                slippage=0.0005,
                fee=0.0005
            )

            if result is None:
                raise ValueError("백테스트 결과가 None입니다")

            trades_per_day = result.trades / total_days if total_days > 0 else 0

            results.append({
                'name': name,
                'leverage': leverage,
                'win_rate': result.win_rate,
                'mdd': result.max_drawdown,
                'profit_factor': result.profit_factor,
                'total_trades': result.trades,
                'trades_per_day': trades_per_day,
                **custom_params
            })

            # 목표 달성 체크
            markers = []
            if result.win_rate >= 80.0:
                markers.append("승률 80%+")
            if result.max_drawdown <= 20.0:
                markers.append("MDD 20%-")

            marker_str = " <- " + ", ".join(markers) if markers else ""

            print(f"  승률: {result.win_rate:.2f}%")
            print(f"  MDD: {result.max_drawdown:.2f}%{marker_str}")
            print(f"  PF: {result.profit_factor:.2f}")
            print(f"  거래 빈도: {trades_per_day:.2f}회/일")

        except Exception as e:
            print(f"  실패: {e}")
            results.append({
                'name': name,
                'leverage': leverage,
                'win_rate': 0,
                'mdd': 100,
                'profit_factor': 0,
                'total_trades': 0,
                'trades_per_day': 0,
                **custom_params
            })

        print()

    # 5. 결과 분석
    print("=" * 80)
    print("결과 분석")
    print("=" * 80)
    print()

    df_results = pd.DataFrame(results)

    # 5-1. 목표 달성 조합 (승률 80%+, MDD 20%-)
    print("1. 목표 달성 조합 (승률 80%+, MDD 20%-)")
    print("-" * 80)

    df_goal = df_results[
        (df_results['win_rate'] >= 80.0) &
        (df_results['mdd'] <= 20.0)
    ].copy()

    if len(df_goal) > 0:
        df_goal = df_goal.sort_values('profit_factor', ascending=False)
        print(f"발견: {len(df_goal)}개 조합")
        print()

        for idx, (_, row) in enumerate(df_goal.iterrows(), 1):
            print(f"{idx}. {row['name']}")
            print(f"   - 승률: {row['win_rate']:.2f}%")
            print(f"   - MDD: {row['mdd']:.2f}%")
            print(f"   - PF: {row['profit_factor']:.2f}")
            print()
    else:
        print("목표 달성 조합 없음")
        print()

    # 5-2. 부분 달성 조합 (MDD 20%- 또는 승률 75%+)
    print("2. 부분 달성 조합 (MDD 20%- 또는 승률 75%+)")
    print("-" * 80)

    df_partial = df_results[
        (df_results['mdd'] <= 20.0) |
        (df_results['win_rate'] >= 75.0)
    ].copy()

    if len(df_partial) > 0:
        df_partial = df_partial.sort_values(['mdd', 'win_rate'], ascending=[True, False])
        print(f"발견: {len(df_partial)}개 조합")
        print()

        for idx, (_, row) in enumerate(df_partial.iterrows(), 1):
            print(f"{idx}. {row['name']}")
            print(f"   - 승률: {row['win_rate']:.2f}%")
            print(f"   - MDD: {row['mdd']:.2f}%")
            print(f"   - PF: {row['profit_factor']:.2f}")
            print()
    else:
        print("부분 달성 조합 없음")
        print()

    # 6. CSV 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"final_combination_results_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"결과 저장: {csv_path}")
    print()

    # 7. 최종 권장사항
    print("=" * 80)
    print("최종 권장사항")
    print("=" * 80)
    print()

    if len(df_goal) > 0:
        best = df_goal.iloc[0]
        print("목표 달성 최고 조합:")
        print(f"  {best['name']}")
        print(f"  - 승률: {best['win_rate']:.2f}%")
        print(f"  - MDD: {best['mdd']:.2f}%")
        print(f"  - PF: {best['profit_factor']:.2f}")
    elif len(df_partial) > 0:
        best = df_partial.iloc[0]
        print("부분 달성 최고 조합:")
        print(f"  {best['name']}")
        print(f"  - 승률: {best['win_rate']:.2f}%")
        print(f"  - MDD: {best['mdd']:.2f}%")
        print(f"  - PF: {best['profit_factor']:.2f}")
    else:
        best = df_results.nsmallest(1, 'mdd').iloc[0]
        print("최저 MDD 조합:")
        print(f"  {best['name']}")
        print(f"  - 승률: {best['win_rate']:.2f}%")
        print(f"  - MDD: {best['mdd']:.2f}%")
        print(f"  - PF: {best['profit_factor']:.2f}")

    print()
    print("=" * 80)
    print("최종 조합 테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_final_combination()
