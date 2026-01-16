#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
filter_tf 가설 검증 스크립트

가설: "filter_tf를 12h/1d로 길게 설정하면 승률이 85%+로 증가한다"

실험 설계:
1. Baseline: filter_tf=4h, entry_validity=6h (현재 프리셋)
2. 실험 1: filter_tf=12h, entry_validity=6h
3. 실험 2: filter_tf=1d, entry_validity=6h
4. 실험 3: filter_tf=12h, entry_validity=48h (문서 권장)

실행 시간: 약 4~5분 (4개 조합)

사용법:
    python tools/test_filter_tf_hypothesis.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from typing import Dict, List

from config.parameters import DEFAULT_PARAMS
from core.optimizer import BacktestOptimizer
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def run_hypothesis_test() -> None:
    """filter_tf 가설 검증 실행"""

    print("=" * 80)
    print("filter_tf 가설 검증 시작")
    print("=" * 80)
    print()

    # 1. 거래소 및 심볼 설정
    exchange = 'bybit'
    symbol = 'BTCUSDT'

    # 2. 데이터 로드
    print(f"데이터 로드 중: {exchange} {symbol}")
    dm = BotDataManager(exchange, symbol)
    if not dm.load_historical():
        print("❌ 데이터 로드 실패")
        return

    if dm.df_entry_full is None or dm.df_entry_full.empty:
        print("❌ 데이터가 비어있습니다")
        return

    df = dm.df_entry_full
    print(f"✅ 데이터 로드 완료: {len(df)}개 캔들")
    print()

    # 3. 테스트 조합 정의
    test_cases = [
        {
            'name': 'Baseline (현재 프리셋)',
            'filter_tf': '4h',
            'entry_validity_hours': 6.0,
        },
        {
            'name': '실험 1 (filter_tf=12h)',
            'filter_tf': '12h',
            'entry_validity_hours': 6.0,
        },
        {
            'name': '실험 2 (filter_tf=1d)',
            'filter_tf': '1d',
            'entry_validity_hours': 6.0,
        },
        {
            'name': '실험 3 (문서 권장)',
            'filter_tf': '12h',
            'entry_validity_hours': 48.0,
        },
    ]

    # 4. Optimizer 초기화 (strategy_class 필수)
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df
    )

    # 4. 각 조합 테스트
    results: List[Dict] = []

    for i, case in enumerate(test_cases, 1):
        print(f"[{i}/4] {case['name']} 테스트 중...")
        print(f"  - filter_tf: {case['filter_tf']}")
        print(f"  - entry_validity_hours: {case['entry_validity_hours']}")

        # 기본 파라미터 복사
        params = DEFAULT_PARAMS.copy()

        # 테스트 파라미터 적용
        params['filter_tf'] = case['filter_tf']
        params['entry_validity_hours'] = case['entry_validity_hours']
        params['max_mdd'] = 100.0  # MDD 제한 해제 (가설 검증용)

        # 백테스트 실행 (_run_single 메서드 사용)
        try:
            # _run_single은 OptimizationResult 객체를 반환
            opt_result = optimizer._run_single(params, slippage=0.0005, fee=0.0005)  # type: ignore[attr-defined]

            if opt_result is None:
                raise ValueError("백테스트 결과가 None입니다")

            # OptimizationResult 객체에서 데이터 추출
            results.append({
                'name': case['name'],
                'filter_tf': case['filter_tf'],
                'entry_validity': case['entry_validity_hours'],
                'win_rate': opt_result.win_rate,  # 이미 퍼센트
                'mdd': opt_result.max_drawdown,  # 이미 퍼센트
                'profit_factor': opt_result.profit_factor,
                'total_trades': opt_result.trades,
                'total_pnl': opt_result.compound_return,  # 복리 수익률
                'grade': opt_result.grade,
            })

            print(f"  ✅ 완료: 승률={opt_result.win_rate:.2f}%, "
                  f"MDD={opt_result.max_drawdown:.2f}%, "
                  f"등급={opt_result.grade}")

        except Exception as e:
            logger.error(f"백테스트 실패: {e}")
            print(f"  ❌ 실패: {e}")
            results.append({
                'name': case['name'],
                'filter_tf': case['filter_tf'],
                'entry_validity': case['entry_validity_hours'],
                'win_rate': 0,
                'mdd': 0,
                'profit_factor': 0,
                'total_trades': 0,
                'total_pnl': 0,
                'grade': 'F',
            })

        print()

    # 5. 결과 비교표 출력
    print("=" * 80)
    print("결과 비교")
    print("=" * 80)
    print()

    # DataFrame 생성
    df = pd.DataFrame(results)

    # 포맷팅
    df_display = df.copy()
    df_display['win_rate'] = df_display['win_rate'].apply(lambda x: f"{x:.2f}%")
    df_display['mdd'] = df_display['mdd'].apply(lambda x: f"{x:.2f}%")
    df_display['profit_factor'] = df_display['profit_factor'].apply(lambda x: f"{x:.2f}")
    df_display['total_pnl'] = df_display['total_pnl'].apply(lambda x: f"{x:.2f}%")

    # 표 출력
    print(df_display.to_string(index=False))
    print()

    # 6. 가설 검증
    print("=" * 80)
    print("가설 검증")
    print("=" * 80)
    print()

    baseline = results[0]
    exp1 = results[1]
    exp2 = results[2]
    exp3 = results[3]

    # Baseline vs 실험 1
    wr_diff_1 = exp1['win_rate'] - baseline['win_rate']
    print(f"1. filter_tf: 4h → 12h (entry_validity=6h 고정)")
    print(f"   승률 변화: {baseline['win_rate']:.2f}% → {exp1['win_rate']:.2f}% "
          f"({'+'if wr_diff_1>=0 else ''}{wr_diff_1:.2f}%p)")
    print(f"   결론: {'✅ 가설 지지' if wr_diff_1 > 1.0 else '❌ 가설 기각'}")
    print()

    # Baseline vs 실험 2
    wr_diff_2 = exp2['win_rate'] - baseline['win_rate']
    print(f"2. filter_tf: 4h → 1d (entry_validity=6h 고정)")
    print(f"   승률 변화: {baseline['win_rate']:.2f}% → {exp2['win_rate']:.2f}% "
          f"({'+'if wr_diff_2>=0 else ''}{wr_diff_2:.2f}%p)")
    print(f"   결론: {'✅ 가설 지지' if wr_diff_2 > 1.0 else '❌ 가설 기각'}")
    print()

    # Baseline vs 실험 3 (문서 권장)
    wr_diff_3 = exp3['win_rate'] - baseline['win_rate']
    trades_diff_3 = exp3['total_trades'] - baseline['total_trades']
    print(f"3. filter_tf=12h + entry_validity=48h (문서 권장)")
    print(f"   승률 변화: {baseline['win_rate']:.2f}% → {exp3['win_rate']:.2f}% "
          f"({'+'if wr_diff_3>=0 else ''}{wr_diff_3:.2f}%p)")
    print(f"   거래수 변화: {baseline['total_trades']} → {exp3['total_trades']} "
          f"({'+'if trades_diff_3>=0 else ''}{trades_diff_3}회)")
    print(f"   목표 달성 여부:")
    print(f"     - 승률 85%+: {'✅' if exp3['win_rate'] >= 85 else '❌'} "
          f"({exp3['win_rate']:.2f}%)")
    print(f"     - 거래수 0.3~0.5회/일: {'✅' if 0.3 <= exp3['total_trades']/len(df) <= 0.5 else '❌'}")
    print(f"   결론: {'✅ 문서 권장값 유효' if wr_diff_3 > 1.0 and exp3['win_rate'] >= 85 else '❌ 추가 조정 필요'}")
    print()

    # 7. 최종 결론
    print("=" * 80)
    print("최종 결론")
    print("=" * 80)
    print()

    best_result = max(results, key=lambda x: x['win_rate'])
    print(f"최고 승률: {best_result['name']} ({best_result['win_rate']:.2f}%)")
    print(f"  - filter_tf: {best_result['filter_tf']}")
    print(f"  - entry_validity: {best_result['entry_validity']}h")
    print(f"  - MDD: {best_result['mdd']:.2f}%")
    print(f"  - Profit Factor: {best_result['profit_factor']:.2f}")
    print(f"  - 등급: {best_result['grade']}")
    print()

    # CSV 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"filter_tf_hypothesis_results_{timestamp}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"결과 저장: {csv_path}")
    print()

    print("=" * 80)
    print("가설 검증 완료")
    print("=" * 80)


if __name__ == "__main__":
    run_hypothesis_test()
