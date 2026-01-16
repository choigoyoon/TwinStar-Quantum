#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
atr_mult 빠른 테스트 - MDD 개선 효과 검증

목표: atr_mult 값에 따른 MDD 변화 확인
테스트: [1.0, 1.25, 1.5, 2.0] 4개 조합
소요 시간: 약 2분

사용법:
    python tools/test_atr_mult_quick.py
"""

import sys
from pathlib import Path

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


def run_atr_mult_test() -> None:
    """atr_mult 빠른 테스트 실행"""

    print("=" * 80)
    print("atr_mult 빠른 테스트 시작")
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
    print(f"✅ 데이터 로드 완료: {len(df):,}개 캔들")
    print(f"기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    print()

    # 3. 테스트 조합 정의
    atr_mult_values = [1.0, 1.25, 1.5, 2.0]

    test_cases = [
        {
            'name': f'atr_mult={val}',
            'atr_mult': val,
        }
        for val in atr_mult_values
    ]

    # 4. Optimizer 초기화
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df
    )

    # 5. 각 조합 테스트
    results: List[Dict] = []

    for i, case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {case['name']} 테스트 중...")

        # 기본 파라미터 복사
        params = DEFAULT_PARAMS.copy()

        # 테스트 파라미터 적용
        params['atr_mult'] = case['atr_mult']
        params['filter_tf'] = '4h'  # 고정
        params['entry_validity_hours'] = 6.0  # 고정
        params['max_mdd'] = 100.0  # MDD 제한 해제

        # 백테스트 실행
        try:
            opt_result = optimizer._run_single(params, slippage=0.0005, fee=0.0005)  # type: ignore[attr-defined]

            if opt_result is None:
                raise ValueError("백테스트 결과가 None입니다")

            # 결과 저장
            results.append({
                'name': case['name'],
                'atr_mult': case['atr_mult'],
                'win_rate': opt_result.win_rate,
                'mdd': opt_result.max_drawdown,
                'profit_factor': opt_result.profit_factor,
                'total_trades': opt_result.trades,
                'total_pnl': opt_result.compound_return,
                'grade': opt_result.grade,
            })

            print(f"  ✅ 완료: 승률={opt_result.win_rate:.2f}%, "
                  f"MDD={opt_result.max_drawdown:.2f}%, "
                  f"PF={opt_result.profit_factor:.2f}, "
                  f"등급={opt_result.grade}")

        except Exception as e:
            logger.error(f"백테스트 실패: {e}")
            print(f"  ❌ 실패: {e}")
            results.append({
                'name': case['name'],
                'atr_mult': case['atr_mult'],
                'win_rate': 0,
                'mdd': 0,
                'profit_factor': 0,
                'total_trades': 0,
                'total_pnl': 0,
                'grade': 'F',
            })

        print()

    # 6. 결과 비교표 출력
    print("=" * 80)
    print("결과 비교")
    print("=" * 80)
    print()

    # DataFrame 생성
    df_results = pd.DataFrame(results)

    # 포맷팅
    df_display = df_results.copy()
    df_display['win_rate'] = df_display['win_rate'].apply(lambda x: f"{x:.2f}%")
    df_display['mdd'] = df_display['mdd'].apply(lambda x: f"{x:.2f}%")
    df_display['profit_factor'] = df_display['profit_factor'].apply(lambda x: f"{x:.2f}")
    df_display['total_pnl'] = df_display['total_pnl'].apply(lambda x: f"{x:.2f}%")

    # 표 출력
    print(df_display.to_string(index=False))
    print()

    # 7. 분석
    print("=" * 80)
    print("atr_mult 효과 분석")
    print("=" * 80)
    print()

    # MDD 기준 정렬
    best_mdd = min(results, key=lambda x: x['mdd'])
    best_pf = max(results, key=lambda x: x['profit_factor'])
    best_wr = max(results, key=lambda x: x['win_rate'])

    print(f"1. MDD 최소: atr_mult={best_mdd['atr_mult']}")
    print(f"   - MDD: {best_mdd['mdd']:.2f}%")
    print(f"   - 승률: {best_mdd['win_rate']:.2f}%")
    print(f"   - PF: {best_mdd['profit_factor']:.2f}")
    print()

    print(f"2. Profit Factor 최대: atr_mult={best_pf['atr_mult']}")
    print(f"   - PF: {best_pf['profit_factor']:.2f}")
    print(f"   - MDD: {best_pf['mdd']:.2f}%")
    print(f"   - 승률: {best_pf['win_rate']:.2f}%")
    print()

    print(f"3. 승률 최고: atr_mult={best_wr['atr_mult']}")
    print(f"   - 승률: {best_wr['win_rate']:.2f}%")
    print(f"   - MDD: {best_wr['mdd']:.2f}%")
    print(f"   - PF: {best_wr['profit_factor']:.2f}")
    print()

    # 8. 트레이드오프 분석
    print("=" * 80)
    print("트레이드오프 분석")
    print("=" * 80)
    print()

    baseline = results[2]  # atr_mult=1.5 (현재 프리셋)

    for result in results:
        if result['atr_mult'] == baseline['atr_mult']:
            continue

        mdd_diff = result['mdd'] - baseline['mdd']
        pf_diff = result['profit_factor'] - baseline['profit_factor']
        wr_diff = result['win_rate'] - baseline['win_rate']

        print(f"atr_mult: 1.5 → {result['atr_mult']}")
        print(f"  - MDD 변화: {baseline['mdd']:.2f}% → {result['mdd']:.2f}% "
              f"({'+'if mdd_diff>=0 else ''}{mdd_diff:.2f}%p)")
        print(f"  - PF 변화: {baseline['profit_factor']:.2f} → {result['profit_factor']:.2f} "
              f"({'+'if pf_diff>=0 else ''}{pf_diff:.2f})")
        print(f"  - 승률 변화: {baseline['win_rate']:.2f}% → {result['win_rate']:.2f}% "
              f"({'+'if wr_diff>=0 else ''}{wr_diff:.2f}%p)")
        print()

    # 9. CSV 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"atr_mult_test_results_{timestamp}.csv"
    df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"결과 저장: {csv_path}")
    print()

    # 10. 권장사항
    print("=" * 80)
    print("권장사항")
    print("=" * 80)
    print()

    # MDD 20% 이하인 조합 찾기
    good_results = [r for r in results if r['mdd'] <= 20.0]

    if good_results:
        print("✅ MDD 20% 이하 달성 조합:")
        for r in good_results:
            print(f"  - atr_mult={r['atr_mult']}: MDD={r['mdd']:.2f}%, "
                  f"승률={r['win_rate']:.2f}%, PF={r['profit_factor']:.2f}")
    else:
        print("⚠️  MDD 20% 이하 달성한 조합 없음")
        print("→ trail_start_r, trail_dist_r 추가 조정 필요")
        print("→ 또는 leverage 축소 필요")

    print()
    print("=" * 80)
    print("atr_mult 테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    run_atr_mult_test()
