#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
leverage 범위 탐색 - MDD 20% 목표

목표: MDD 20% 이하를 달성하는 leverage 찾기

테스트 범위:
- leverage: [1, 2, 3, 4, 5] (5개)
- 총 조합: 5개

고정값: DEFAULT_PARAMS 최적 조합
- atr_mult: 1.25
- trail_start_r: 0.8
- trail_dist_r: 0.1
- entry_validity_hours: 6.0

예상 소요 시간: 약 2.5분
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

def optimize_leverage():
    """leverage 범위 최적화"""

    print("=" * 80)
    print("leverage 범위 최적화 - MDD 20% 목표")
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

    # 2. leverage 범위
    leverage_values = [1, 2, 3, 4, 5]

    print("테스트 범위:")
    print(f"  - leverage: {leverage_values}")
    print(f"  - 총 조합: {len(leverage_values)}개")
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

    for idx, leverage in enumerate(leverage_values, 1):
        print(f"[{idx}/{len(leverage_values)}] leverage={leverage}x")

        # 파라미터 설정
        params = DEFAULT_PARAMS.copy()
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
                'leverage': leverage,
                'win_rate': result.win_rate,
                'mdd': result.max_drawdown,
                'profit_factor': result.profit_factor,
                'total_trades': result.trades,
                'trades_per_day': trades_per_day
            })

            # MDD 20% 이하 체크
            mdd_marker = " <- MDD 20% 이하!" if result.max_drawdown <= 20.0 else ""

            print(f"  승률: {result.win_rate:.2f}%")
            print(f"  MDD: {result.max_drawdown:.2f}%{mdd_marker}")
            print(f"  PF: {result.profit_factor:.2f}")
            print(f"  거래 빈도: {trades_per_day:.2f}회/일")

        except Exception as e:
            print(f"  실패: {e}")
            results.append({
                'leverage': leverage,
                'win_rate': 0,
                'mdd': 100,
                'profit_factor': 0,
                'total_trades': 0,
                'trades_per_day': 0
            })

        print()

    # 5. 결과 분석
    print("=" * 80)
    print("결과 분석")
    print("=" * 80)
    print()

    df_results = pd.DataFrame(results)

    # 5-1. MDD 20% 이하 조합
    print("1. MDD 20% 이하 조합")
    print("-" * 80)

    df_low_mdd = df_results[df_results['mdd'] <= 20.0].copy()

    if len(df_low_mdd) > 0:
        df_low_mdd = df_low_mdd.sort_values('win_rate', ascending=False)
        print(f"발견: {len(df_low_mdd)}개 조합")
        print()

        for idx, (_, row) in enumerate(df_low_mdd.iterrows(), 1):
            print(f"{idx}. leverage={row['leverage']:.0f}x")
            print(f"   - 승률: {row['win_rate']:.2f}%")
            print(f"   - MDD: {row['mdd']:.2f}%")
            print(f"   - PF: {row['profit_factor']:.2f}")
            print()
    else:
        print("MDD 20% 이하 조합 없음")
        print()

        # MDD 최저값 찾기
        best_mdd = df_results.nsmallest(1, 'mdd').iloc[0]
        print(f"최저 MDD: {best_mdd['mdd']:.2f}% (leverage={best_mdd['leverage']:.0f}x)")
        print()

    # 5-2. leverage별 MDD 추세
    print("2. leverage vs MDD 추세")
    print("-" * 80)

    for _, row in df_results.iterrows():
        print(f"leverage={row['leverage']:.0f}x: MDD={row['mdd']:.2f}%")

    print()

    # 6. CSV 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"leverage_optimization_results_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"결과 저장: {csv_path}")
    print()

    # 7. 최종 권장사항
    print("=" * 80)
    print("최종 권장사항")
    print("=" * 80)
    print()

    if len(df_low_mdd) > 0:
        best = df_low_mdd.iloc[0]
        print("MDD 20% 이하 최고 승률:")
        print(f"  leverage: {best['leverage']:.0f}x")
        print(f"  승률: {best['win_rate']:.2f}%")
        print(f"  MDD: {best['mdd']:.2f}%")
        print(f"  PF: {best['profit_factor']:.2f}")
    else:
        best_mdd = df_results.nsmallest(1, 'mdd').iloc[0]
        print("최저 MDD 조합:")
        print(f"  leverage: {best_mdd['leverage']:.0f}x")
        print(f"  승률: {best_mdd['win_rate']:.2f}%")
        print(f"  MDD: {best_mdd['mdd']:.2f}%")
        print(f"  PF: {best_mdd['profit_factor']:.2f}")

    print()
    print("=" * 80)
    print("leverage 최적화 완료")
    print("=" * 80)


if __name__ == "__main__":
    optimize_leverage()
