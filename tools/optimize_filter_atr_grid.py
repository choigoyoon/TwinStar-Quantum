#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
filter_tf × atr_mult 그리드 서치 - 최적 파라미터 범위 도출

목표: 전체 파라미터 공간을 탐색하여 실전 매매에 적합한 조합 발견

테스트 범위:
- filter_tf: ['2h', '4h', '6h', '12h'] (4개)
- atr_mult: [1.0, 1.25, 1.5, 2.0, 2.5, 3.0] (6개)
- 총 조합: 24개

예상 소요 시간: 약 12분

사용법:
    python tools/optimize_filter_atr_grid.py
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
    """
    거래 빈도 적합도 점수 계산

    최적 범위: 0.5~1.0 회/일
    - 0.5~1.0: 100점
    - < 0.5: 비례 감소
    - > 1.0: 과도한 거래로 감점
    """
    if 0.5 <= trades_per_day <= 1.0:
        return 100.0
    elif trades_per_day < 0.5:
        return (trades_per_day / 0.5) * 100.0
    else:  # > 1.0
        return max(0.0, 100.0 - (trades_per_day - 1.0) * 50.0)


def calculate_trading_suitability_score(
    win_rate: float,
    mdd: float,
    profit_factor: float,
    trades_per_day: float
) -> float:
    """
    실전 매매 적합성 점수 계산

    Args:
        win_rate: 승률 (%)
        mdd: 최대 낙폭 (%)
        profit_factor: Profit Factor
        trades_per_day: 거래 빈도 (회/일)

    Returns:
        적합성 점수 (0~100)
    """
    # 1. 승률 점수 (30% 가중치)
    win_rate_score = win_rate * 0.3

    # 2. MDD 점수 (40% 가중치) - 낮을수록 좋음
    mdd_score = (100 - mdd) * 0.4

    # 3. Profit Factor 점수 (20% 가중치) - 5.0 이상은 동일 취급
    pf_capped = min(profit_factor, 5.0)
    pf_score = pf_capped * 10 * 0.2  # PF 5.0 = 50점

    # 4. 거래 빈도 점수 (10% 가중치)
    freq_score = calculate_trade_frequency_score(trades_per_day) * 0.1

    total_score = win_rate_score + mdd_score + pf_score + freq_score

    return total_score


def run_grid_search() -> None:
    """filter_tf × atr_mult 그리드 서치 실행"""

    print("=" * 80)
    print("filter_tf × atr_mult 그리드 서치")
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
    filter_tf_values = ['2h', '4h', '6h', '12h']
    atr_mult_values = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0]

    total_combinations = len(filter_tf_values) * len(atr_mult_values)
    print(f"그리드 설정")
    print(f"  - filter_tf: {filter_tf_values}")
    print(f"  - atr_mult: {atr_mult_values}")
    print(f"  - 총 조합: {total_combinations}개")
    print(f"  - 예상 소요 시간: 약 {total_combinations * 0.5:.0f}분")
    print()

    # 3. Optimizer 초기화
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df
    )

    # 4. 그리드 서치 실행
    results: List[Dict] = []
    combo_count = 0

    print("그리드 서치 시작...")
    print()

    for filter_tf in filter_tf_values:
        for atr_mult in atr_mult_values:
            combo_count += 1
            print(f"[{combo_count}/{total_combinations}] filter_tf={filter_tf}, atr_mult={atr_mult} 테스트 중...")

            # 파라미터 설정
            params = DEFAULT_PARAMS.copy()
            params['filter_tf'] = filter_tf
            params['atr_mult'] = atr_mult
            params['entry_validity_hours'] = 6.0  # 고정
            params['max_mdd'] = 100.0  # MDD 제한 해제

            # 백테스트 실행
            try:
                opt_result = optimizer._run_single(params, slippage=0.0005, fee=0.0005)  # type: ignore[attr-defined]

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
                    'filter_tf': filter_tf,
                    'atr_mult': atr_mult,
                    'win_rate': opt_result.win_rate,
                    'mdd': opt_result.max_drawdown,
                    'profit_factor': opt_result.profit_factor,
                    'total_trades': opt_result.trades,
                    'trades_per_day': trades_per_day,
                    'suitability_score': suitability_score,
                    'grade': opt_result.grade,
                })

                print(f"  완료: 승률={opt_result.win_rate:.2f}%, MDD={opt_result.max_drawdown:.2f}%, "
                      f"PF={opt_result.profit_factor:.2f}, 빈도={trades_per_day:.2f}회/일, "
                      f"점수={suitability_score:.1f}, 등급={opt_result.grade}")

            except Exception as e:
                logger.error(f"백테스트 실패: {e}")
                print(f"  실패: {e}")
                results.append({
                    'filter_tf': filter_tf,
                    'atr_mult': atr_mult,
                    'win_rate': 0,
                    'mdd': 100,
                    'profit_factor': 0,
                    'total_trades': 0,
                    'trades_per_day': 0,
                    'suitability_score': 0,
                    'grade': 'F',
                })

            print()

    # 5. 결과 분석
    print("=" * 80)
    print("그리드 서치 결과 분석")
    print("=" * 80)
    print()

    # DataFrame 생성
    df_results = pd.DataFrame(results)

    # 5-1. 전체 결과 테이블
    print("1. 전체 결과 (24개 조합)")
    print("-" * 80)
    df_display = df_results.copy()
    df_display = df_display.sort_values('suitability_score', ascending=False)
    df_display['win_rate'] = df_display['win_rate'].apply(lambda x: f"{x:.1f}%")
    df_display['mdd'] = df_display['mdd'].apply(lambda x: f"{x:.1f}%")
    df_display['profit_factor'] = df_display['profit_factor'].apply(lambda x: f"{x:.2f}")
    df_display['trades_per_day'] = df_display['trades_per_day'].apply(lambda x: f"{x:.2f}")
    df_display['suitability_score'] = df_display['suitability_score'].apply(lambda x: f"{x:.1f}")
    # grade 컬럼 제거 (이모지 인코딩 문제)
    df_display = df_display.drop(columns=['grade'], errors='ignore')
    print(df_display.to_string(index=False))
    print()

    # 5-2. MDD 20% 이하 필터링
    print("2. MDD 20% 이하 조합")
    print("-" * 80)
    df_low_mdd = df_results[df_results['mdd'] <= 20.0].copy()
    if len(df_low_mdd) > 0:
        df_low_mdd = df_low_mdd.sort_values('suitability_score', ascending=False)
        print(f"발견: {len(df_low_mdd)}개 조합")
        print()
        for idx, row in df_low_mdd.iterrows():
            print(f"  - filter_tf={row['filter_tf']}, atr_mult={row['atr_mult']}: "
                  f"MDD={row['mdd']:.2f}%, 승률={row['win_rate']:.2f}%, "
                  f"PF={row['profit_factor']:.2f}, 점수={row['suitability_score']:.1f}")
    else:
        print("MDD 20% 이하 조합 없음")
    print()

    # 5-3. 적합성 점수 Top 5
    print("3. 적합성 점수 Top 5")
    print("-" * 80)
    df_top5 = df_results.nlargest(5, 'suitability_score')
    for rank, (idx, row) in enumerate(df_top5.iterrows(), 1):
        print(f"{rank}. filter_tf={row['filter_tf']}, atr_mult={row['atr_mult']}")
        print(f"   - 적합성 점수: {row['suitability_score']:.1f}")
        print(f"   - 승률: {row['win_rate']:.2f}%")
        print(f"   - MDD: {row['mdd']:.2f}%")
        print(f"   - Profit Factor: {row['profit_factor']:.2f}")
        print(f"   - 거래 빈도: {row['trades_per_day']:.2f}회/일")
        print()

    # 5-4. filter_tf별 최적 atr_mult
    print("4. filter_tf별 최적 atr_mult")
    print("-" * 80)
    for filter_tf in filter_tf_values:
        df_filter = df_results[df_results['filter_tf'] == filter_tf]
        best = df_filter.nlargest(1, 'suitability_score').iloc[0]
        print(f"filter_tf={filter_tf}:")
        print(f"  → 최적 atr_mult={best['atr_mult']}")
        print(f"     승률={best['win_rate']:.2f}%, MDD={best['mdd']:.2f}%, "
              f"PF={best['profit_factor']:.2f}, 점수={best['suitability_score']:.1f}")
        print()

    # 5-5. 히트맵 데이터 생성
    print("5. MDD 히트맵 (filter_tf × atr_mult)")
    print("-" * 80)
    pivot_mdd = df_results.pivot(index='filter_tf', columns='atr_mult', values='mdd')
    pivot_mdd = pivot_mdd.reindex(filter_tf_values)  # 순서 유지
    print(pivot_mdd.to_string(float_format=lambda x: f"{x:.1f}%"))
    print()

    print("6. 적합성 점수 히트맵 (filter_tf × atr_mult)")
    print("-" * 80)
    pivot_score = df_results.pivot(index='filter_tf', columns='atr_mult', values='suitability_score')
    pivot_score = pivot_score.reindex(filter_tf_values)  # 순서 유지
    print(pivot_score.to_string(float_format=lambda x: f"{x:.1f}"))
    print()

    print("7. 승률 히트맵 (filter_tf × atr_mult)")
    print("-" * 80)
    pivot_wr = df_results.pivot(index='filter_tf', columns='atr_mult', values='win_rate')
    pivot_wr = pivot_wr.reindex(filter_tf_values)  # 순서 유지
    print(pivot_wr.to_string(float_format=lambda x: f"{x:.1f}%"))
    print()

    # 6. CSV 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"grid_search_results_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"결과 저장: {csv_path}")
    print()

    # 7. 권장사항
    print("=" * 80)
    print("권장사항")
    print("=" * 80)
    print()

    best_overall = df_results.nlargest(1, 'suitability_score').iloc[0]
    print(f"최고 적합성 점수 조합:")
    print(f"   filter_tf={best_overall['filter_tf']}, atr_mult={best_overall['atr_mult']}")
    print(f"   - 점수: {best_overall['suitability_score']:.1f}")
    print(f"   - 승률: {best_overall['win_rate']:.2f}%")
    print(f"   - MDD: {best_overall['mdd']:.2f}%")
    print(f"   - Profit Factor: {best_overall['profit_factor']:.2f}")
    print(f"   - 거래 빈도: {best_overall['trades_per_day']:.2f}회/일")
    print()

    # MDD 기준 추천
    df_acceptable_mdd = df_results[df_results['mdd'] <= 25.0]
    if len(df_acceptable_mdd) > 0:
        best_acceptable = df_acceptable_mdd.nlargest(1, 'suitability_score').iloc[0]
        print(f"MDD 25% 이하 최적 조합:")
        print(f"   filter_tf={best_acceptable['filter_tf']}, atr_mult={best_acceptable['atr_mult']}")
        print(f"   - 점수: {best_acceptable['suitability_score']:.1f}")
        print(f"   - 승률: {best_acceptable['win_rate']:.2f}%")
        print(f"   - MDD: {best_acceptable['mdd']:.2f}%")
        print(f"   - Profit Factor: {best_acceptable['profit_factor']:.2f}")
        print(f"   - 거래 빈도: {best_acceptable['trades_per_day']:.2f}회/일")
        print()

    # 패턴 분석
    print("패턴 분석:")
    print()

    # filter_tf 평균 MDD
    print("  filter_tf별 평균 MDD:")
    for filter_tf in filter_tf_values:
        avg_mdd = df_results[df_results['filter_tf'] == filter_tf]['mdd'].mean()
        print(f"    - {filter_tf}: {avg_mdd:.1f}%")
    print()

    # atr_mult 평균 MDD
    print("  atr_mult별 평균 MDD:")
    for atr_mult in atr_mult_values:
        avg_mdd = df_results[df_results['atr_mult'] == atr_mult]['mdd'].mean()
        print(f"    - {atr_mult}: {avg_mdd:.1f}%")
    print()

    print("=" * 80)
    print("그리드 서치 완료")
    print("=" * 80)


if __name__ == "__main__":
    run_grid_search()
