#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
이전 최적 파라미터 검증 (MDD 9.2% 달성했던 조합)

목표: 이전 최적 파라미터가 현재 데이터에서도 동일한 성능을 내는지 확인
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.parameters import DEFAULT_PARAMS
from core.optimizer import BacktestOptimizer
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core

def test_previous_optimal():
    """이전 최적 파라미터 테스트"""

    print("=" * 80)
    print("이전 최적 파라미터 검증")
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

    # 2. 이전 최적 파라미터 (DEFAULT_PARAMS 기반)
    print("테스트 파라미터:")
    print("-" * 80)

    # 테스트 1: DEFAULT_PARAMS 그대로 (leverage=10)
    params_10x = DEFAULT_PARAMS.copy()
    params_10x['max_mdd'] = 100.0

    print("Test 1: DEFAULT_PARAMS (leverage=10x)")
    print(f"  - atr_mult: {params_10x['atr_mult']}")
    print(f"  - trail_start_r: {params_10x['trail_start_r']}")
    print(f"  - trail_dist_r: {params_10x['trail_dist_r']}")
    print(f"  - entry_validity_hours: {params_10x['entry_validity_hours']}")
    print(f"  - leverage: {params_10x['leverage']}")
    print()

    # 테스트 2: leverage=3x로 변경 (이전 최적 레버리지)
    params_3x = DEFAULT_PARAMS.copy()
    params_3x['leverage'] = 3
    params_3x['max_mdd'] = 100.0

    print("Test 2: DEFAULT_PARAMS (leverage=3x)")
    print(f"  - atr_mult: {params_3x['atr_mult']}")
    print(f"  - trail_start_r: {params_3x['trail_start_r']}")
    print(f"  - trail_dist_r: {params_3x['trail_dist_r']}")
    print(f"  - entry_validity_hours: {params_3x['entry_validity_hours']}")
    print(f"  - leverage: {params_3x['leverage']}")
    print()

    # 3. Optimizer 초기화
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df
    )

    # 4. 백테스트 실행
    print("백테스트 실행 중...")
    print("=" * 80)
    print()

    results = []

    for idx, (name, params) in enumerate([
        ("DEFAULT_PARAMS (10x)", params_10x),
        ("DEFAULT_PARAMS (3x)", params_3x)
    ], 1):
        print(f"[{idx}/2] {name}")

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
                'leverage': params['leverage'],
                'win_rate': result.win_rate,
                'mdd': result.max_drawdown,
                'profit_factor': result.profit_factor,
                'total_trades': result.trades,
                'trades_per_day': trades_per_day
            })

            print(f"  승률: {result.win_rate:.2f}%")
            print(f"  MDD: {result.max_drawdown:.2f}%")
            print(f"  PF: {result.profit_factor:.2f}")
            print(f"  거래수: {result.trades}회")
            print(f"  거래 빈도: {trades_per_day:.2f}회/일")

            # MDD 20% 이하 체크
            if result.max_drawdown <= 20.0:
                print("  ✅ MDD 20% 이하 달성!")

        except Exception as e:
            print(f"  ❌ 실패: {e}")
            results.append({
                'name': name,
                'leverage': params['leverage'],
                'win_rate': 0,
                'mdd': 100,
                'profit_factor': 0,
                'total_trades': 0,
                'trades_per_day': 0
            })

        print()

    # 5. 결과 요약
    print("=" * 80)
    print("결과 요약")
    print("=" * 80)
    print()

    for r in results:
        print(f"{r['name']}:")
        print(f"  승률: {r['win_rate']:.2f}%")
        print(f"  MDD: {r['mdd']:.2f}%")
        print(f"  PF: {r['profit_factor']:.2f}")
        print(f"  거래 빈도: {r['trades_per_day']:.2f}회/일")
        print()

    # 6. 이전 최적 성능과 비교
    print("=" * 80)
    print("이전 최적 성능과 비교")
    print("=" * 80)
    print()
    print("이전 (2026-01-01 최적화):")
    print("  - 승률: 84.3%")
    print("  - MDD: 9.2%")
    print("  - leverage: 3x")
    print()

    if len(results) >= 2:
        current_3x = results[1]  # leverage=3x 결과
        print("현재 (동일 파라미터, 새 데이터):")
        print(f"  - 승률: {current_3x['win_rate']:.2f}%")
        print(f"  - MDD: {current_3x['mdd']:.2f}%")
        print(f"  - leverage: 3x")
        print()

        if current_3x['mdd'] > 20.0:
            print("⚠️ MDD 20% 초과")
            print("   원인: 데이터 기간 변경 또는 시장 환경 변화")
            print("   해결: 파라미터 재최적화 필요")
        else:
            print("✅ MDD 20% 이하 달성!")


if __name__ == "__main__":
    test_previous_optimal()
