#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
trail + entry_validity 종합 최적화 - MDD 20% 목표

목표: MDD 35% → 20% 이하 달성

테스트 범위:
- trail_start_r: [1.0, 1.2, 1.5] (3개)
- entry_validity_hours: [6.0, 24.0, 48.0, 72.0] (4개)
- trail_dist_r: [0.02, 0.03, 0.05] (3개)
- 총 조합: 3×4×3 = 36개

고정값:
- filter_tf: '4h' (최적 확인됨)
- atr_mult: 1.5 (최적 확인됨)
- leverage: DEFAULT_PARAMS['leverage'] (3x)

예상 소요 시간: 약 18분

사용법:
    python tools/optimize_trail_comprehensive.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List

from config.parameters import DEFAULT_PARAMS
from core.optimizer import BacktestOptimizer
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def calculate_trade_frequency_score(trades_per_day: float) -> float:
    """거래 빈도 적합도 점수 (0.5~1.0 회/일 최적)"""
    if 0.5 <= trades_per_day <= 1.0:
        return 100.0
    elif trades_per_day < 0.5:
        return (trades_per_day / 0.5) * 100.0
    else:
        return max(0.0, 100.0 - (trades_per_day - 1.0) * 50.0)


def calculate_trading_suitability_score(
    win_rate: float,
    mdd: float,
    profit_factor: float,
    trades_per_day: float
) -> float:
    """실전 매매 적합성 점수 (0~100)"""
    win_rate_score = win_rate * 0.3
    mdd_score = (100 - mdd) * 0.4
    pf_capped = min(profit_factor, 5.0)
    pf_score = pf_capped * 10 * 0.2
    freq_score = calculate_trade_frequency_score(trades_per_day) * 0.1
    return win_rate_score + mdd_score + pf_score + freq_score


def run_comprehensive_optimization() -> None:
    """종합 최적화 실행"""

    print("=" * 80)
    print("trail + entry_validity 종합 최적화")
    print("=" * 80)
    print()

    # 1. 데이터 로드
    print("데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT')
    if not dm.load_historical():
        print("데이터 로드 실패")
        return

    if dm.df_entry_full is None or dm.df_entry_full.empty:
        print("데이터가 비어있습니다")
        return

    df = dm.df_entry_full
    total_days = (df['timestamp'].max() - df['timestamp'].min()).days
    print(f"데이터 로드 완료: {len(df):,}개 캔들 ({total_days}일)")
    print()

    # 2. 그리드 파라미터 정의
    trail_start_r_values = [1.0, 1.2, 1.5]
    entry_validity_values = [6.0, 24.0, 48.0, 72.0]
    trail_dist_r_values = [0.02, 0.03, 0.05]

    # 고정값
    filter_tf = '4h'
    atr_mult = 1.5

    total_combinations = (
        len(trail_start_r_values) *
        len(entry_validity_values) *
        len(trail_dist_r_values)
    )

    print(f"그리드 설정")
    print(f"  고정값:")
    print(f"    - filter_tf: {filter_tf}")
    print(f"    - atr_mult: {atr_mult}")
    print(f"  변수:")
    print(f"    - trail_start_r: {trail_start_r_values}")
    print(f"    - entry_validity_hours: {entry_validity_values}")
    print(f"    - trail_dist_r: {trail_dist_r_values}")
    print(f"  총 조합: {total_combinations}개")
    print(f"  예상 소요 시간: 약 {total_combinations * 0.5:.0f}분")
    print()

    # 3. Optimizer 초기화
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df
    )

    # 4. 그리드 서치 실행
    results: List[Dict] = []
    combo_count = 0

    print("종합 최적화 시작...")
    print()

    for trail_start_r in trail_start_r_values:
        for entry_validity in entry_validity_values:
            for trail_dist_r in trail_dist_r_values:
                combo_count += 1

                print(f"[{combo_count}/{total_combinations}] "
                      f"trail_start={trail_start_r}, entry_valid={entry_validity}h, "
                      f"trail_dist={trail_dist_r}")

                # 파라미터 설정
                params = DEFAULT_PARAMS.copy()
                params['filter_tf'] = filter_tf
                params['atr_mult'] = atr_mult
                params['trail_start_r'] = trail_start_r
                params['entry_validity_hours'] = entry_validity
                params['trail_dist_r'] = trail_dist_r
                params['max_mdd'] = 100.0

                # 백테스트 실행
                try:
                    opt_result = optimizer._run_single(
                        params,
                        slippage=0.0005,
                        fee=0.0005
                    )  # type: ignore[attr-defined]

                    if opt_result is None:
                        raise ValueError("백테스트 결과가 None입니다")

                    # 거래 빈도 계산
                    trades_per_day = opt_result.trades / total_days if total_days > 0 else 0

                    # 적합성 점수 계산
                    suitability_score = calculate_trading_suitability_score(
                        win_rate=opt_result.win_rate,
                        mdd=opt_result.max_drawdown,
                        profit_factor=opt_result.profit_factor,
                        trades_per_day=trades_per_day
                    )

                    # 결과 저장
                    results.append({
                        'trail_start_r': trail_start_r,
                        'entry_validity_hours': entry_validity,
                        'trail_dist_r': trail_dist_r,
                        'win_rate': opt_result.win_rate,
                        'mdd': opt_result.max_drawdown,
                        'profit_factor': opt_result.profit_factor,
                        'total_trades': opt_result.trades,
                        'trades_per_day': trades_per_day,
                        'suitability_score': suitability_score,
                        'leverage': params['leverage'],  # 추가: leverage 저장
                    })

                    # MDD 20% 이하면 강조 표시
                    mdd_marker = " <- MDD 20% 이하!" if opt_result.max_drawdown <= 20.0 else ""

                    print(f"  승률={opt_result.win_rate:.2f}%, MDD={opt_result.max_drawdown:.2f}%, "
                          f"PF={opt_result.profit_factor:.2f}, 빈도={trades_per_day:.2f}, "
                          f"점수={suitability_score:.1f}{mdd_marker}")

                except Exception as e:
                    logger.error(f"백테스트 실패: {e}")
                    print(f"  실패: {e}")
                    results.append({
                        'trail_start_r': trail_start_r,
                        'entry_validity_hours': entry_validity,
                        'trail_dist_r': trail_dist_r,
                        'win_rate': 0,
                        'mdd': 100,
                        'profit_factor': 0,
                        'total_trades': 0,
                        'trades_per_day': 0,
                        'suitability_score': 0,
                        'leverage': params.get('leverage', DEFAULT_PARAMS.get('leverage', 3)),  # 추가: leverage 저장
                    })

                print()

    # 5. 결과 분석
    print("=" * 80)
    print("종합 최적화 결과 분석")
    print("=" * 80)
    print()

    df_results = pd.DataFrame(results)

    # 5-1. MDD 20% 이하 조합 (최우선)
    print("1. MDD 20% 이하 조합")
    print("-" * 80)
    df_low_mdd = df_results[df_results['mdd'] <= 20.0].copy()

    if len(df_low_mdd) > 0:
        df_low_mdd = df_low_mdd.sort_values('suitability_score', ascending=False)
        print(f"발견: {len(df_low_mdd)}개 조합")
        print()

        for idx, (_, row) in enumerate(df_low_mdd.iterrows(), 1):
            print(f"{idx}. trail_start={row['trail_start_r']}, "
                  f"entry_valid={row['entry_validity_hours']:.0f}h, "
                  f"trail_dist={row['trail_dist_r']}, lev={row['leverage']}x")
            print(f"   - 점수: {row['suitability_score']:.1f}")
            print(f"   - 승률: {row['win_rate']:.2f}%")
            print(f"   - MDD: {row['mdd']:.2f}%")
            print(f"   - PF: {row['profit_factor']:.2f}")
            print(f"   - 거래 빈도: {row['trades_per_day']:.2f}회/일")
            print()
    else:
        print("MDD 20% 이하 조합 없음")
        print()

        # MDD 25% 이하로 완화
        df_acceptable = df_results[df_results['mdd'] <= 25.0].copy()
        if len(df_acceptable) > 0:
            df_acceptable = df_acceptable.sort_values('suitability_score', ascending=False)
            best = df_acceptable.iloc[0]
            print("MDD 25% 이하 최적 조합:")
            print(f"  trail_start={best['trail_start_r']}, "
                  f"entry_valid={best['entry_validity_hours']:.0f}h, "
                  f"trail_dist={best['trail_dist_r']}, lev={best['leverage']}x")
            print(f"  - MDD: {best['mdd']:.2f}%")
            print(f"  - 승률: {best['win_rate']:.2f}%")
            print(f"  - PF: {best['profit_factor']:.2f}")
            print()

    # 5-2. 적합성 점수 Top 10
    print("2. 적합성 점수 Top 10")
    print("-" * 80)
    df_top10 = df_results.nlargest(10, 'suitability_score')

    for rank, (_, row) in enumerate(df_top10.iterrows(), 1):
        print(f"{rank}. trail_start={row['trail_start_r']}, "
              f"entry_valid={row['entry_validity_hours']:.0f}h, "
              f"trail_dist={row['trail_dist_r']}, lev={row['leverage']}x")
        print(f"   점수={row['suitability_score']:.1f}, "
              f"승률={row['win_rate']:.2f}%, MDD={row['mdd']:.2f}%, "
              f"PF={row['profit_factor']:.2f}")
        print()

    # 5-3. leverage 영향 분석 (생략 - leverage는 고정값 사용)
    # 이 스크립트는 leverage를 변수로 사용하지 않음
    # DEFAULT_PARAMS의 기본 leverage 값(3x) 사용
    print("3. leverage 영향 분석")
    print("-" * 80)
    print(f"  leverage는 고정값 사용 (DEFAULT_PARAMS['leverage'] = {DEFAULT_PARAMS.get('leverage', 3)}x)")
    print("  다양한 leverage 테스트가 필요하면 그리드에 추가 필요")
    print()

    # 5-4. trail_start_r 영향 분석
    print("4. trail_start_r 영향 분석")
    print("-" * 80)

    for trail_start in trail_start_r_values:
        df_trail = df_results[df_results['trail_start_r'] == trail_start]
        avg_mdd = df_trail['mdd'].mean()
        avg_pf = df_trail['profit_factor'].mean()

        print(f"trail_start_r={trail_start}:")
        print(f"  - 평균 MDD: {avg_mdd:.2f}%")
        print(f"  - 평균 PF: {avg_pf:.2f}")
        print()

    # 5-5. entry_validity_hours 영향 분석
    print("5. entry_validity_hours 영향 분석")
    print("-" * 80)

    for entry_valid in entry_validity_values:
        df_entry = df_results[df_results['entry_validity_hours'] == entry_valid]
        avg_mdd = df_entry['mdd'].mean()
        avg_trades = df_entry['trades_per_day'].mean()

        print(f"entry_validity={entry_valid:.0f}h:")
        print(f"  - 평균 MDD: {avg_mdd:.2f}%")
        print(f"  - 평균 거래 빈도: {avg_trades:.2f}회/일")
        print()

    # 6. CSV 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"trail_optimization_results_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"결과 저장: {csv_path}")
    print()

    # 7. 최종 권장사항
    print("=" * 80)
    print("최종 권장사항")
    print("=" * 80)
    print()

    best_overall = df_results.nlargest(1, 'suitability_score').iloc[0]
    print("최고 적합성 점수 조합:")
    print(f"  trail_start_r: {best_overall['trail_start_r']}")
    print(f"  entry_validity_hours: {best_overall['entry_validity_hours']:.0f}")
    print(f"  trail_dist_r: {best_overall['trail_dist_r']}")
    print(f"  leverage: {best_overall['leverage']}")
    print(f"  (filter_tf='4h', atr_mult=1.5)")
    print()
    print(f"  - 적합성 점수: {best_overall['suitability_score']:.1f}")
    print(f"  - 승률: {best_overall['win_rate']:.2f}%")
    print(f"  - MDD: {best_overall['mdd']:.2f}%")
    print(f"  - Profit Factor: {best_overall['profit_factor']:.2f}")
    print(f"  - 거래 빈도: {best_overall['trades_per_day']:.2f}회/일")
    print()

    # MDD 기준 최적 조합
    if len(df_low_mdd) > 0:
        best_mdd = df_low_mdd.iloc[0]
        print("MDD 20% 이하 최고 점수 조합:")
        print(f"  trail_start_r: {best_mdd['trail_start_r']}")
        print(f"  entry_validity_hours: {best_mdd['entry_validity_hours']:.0f}")
        print(f"  trail_dist_r: {best_mdd['trail_dist_r']}")
        print(f"  leverage: {best_mdd['leverage']}")
        print()
        print(f"  - MDD: {best_mdd['mdd']:.2f}%")
        print(f"  - 승률: {best_mdd['win_rate']:.2f}%")
        print(f"  - Profit Factor: {best_mdd['profit_factor']:.2f}")
        print()

    print("=" * 80)
    print("종합 최적화 완료")
    print("=" * 80)


if __name__ == "__main__":
    run_comprehensive_optimization()
