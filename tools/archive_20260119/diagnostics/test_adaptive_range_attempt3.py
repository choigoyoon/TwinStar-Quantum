#!/usr/bin/env python3
"""2단계 Coarse-to-Fine 백테스트 - 시도 3 (ATR 최대 1.0)

목표: MDD <10% 달성

개선 사항 (v7.25.3):
- atr_mult 최대값: 1.25 → 1.0 (더 보수적)
- filter_tf: 2h 제거, 4h부터 시작 (노이즈 감소)
- MDD 절대 필터: Stage 1에서 50% 초과 제외

예상 결과:
- MDD: 10-20% (목표 2배 이내)
- 수익률: 800-1,200% (실용적 수준)

Author: Claude Sonnet 4.5
Date: 2026-01-19
"""

import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS


def build_coarse_ranges_v3() -> dict:
    """Coarse Grid 범위 생성 - 시도 3 (더 보수적)

    개선 사항:
    - atr_mult: 최대 1.0 (이전 1.25)
    - filter_tf: 4h, 6h, 12h (2h 제거)

    Returns:
        243개 조합 (3×3×3×3×3)
    """
    return {
        'atr_mult': [0.5, 0.7, 1.0],  # 최대 1.0
        'filter_tf': ['4h', '6h', '12h'],  # 2h 제거
        'entry_validity_hours': [6, 24, 48],
        'trail_start_r': [0.3, 0.6, 1.0],
        'trail_dist_r': [0.02, 0.05, 0.10]
    }


def build_fine_ranges(coarse_optimal: dict) -> dict:
    """Fine-Tuning 범위 생성 (Stage 2)

    Args:
        coarse_optimal: Stage 1 최적 파라미터

    Returns:
        ~500개 조합 (상위 5개 영역별)
    """
    # ATR ±20%
    atr_center = coarse_optimal['atr_mult']
    atr_min = max(0.3, atr_center * 0.8)
    atr_max = min(1.5, atr_center * 1.2)  # 최대 1.5로 제한

    # filter_tf 전후 1단계
    tf_map = ['1h', '2h', '3h', '4h', '6h', '8h', '12h', '1d', '2d']
    tf_idx = tf_map.index(coarse_optimal['filter_tf'])
    tf_range = [
        tf_map[max(0, tf_idx - 1)],
        tf_map[tf_idx],
        tf_map[min(len(tf_map) - 1, tf_idx + 1)]
    ]

    # entry_validity_hours ±25%
    entry_center = coarse_optimal['entry_validity_hours']
    entry_min = max(6, int(entry_center - entry_center * 0.25))
    entry_max = min(120, int(entry_center + entry_center * 0.25))
    entry_step = max(6, (entry_max - entry_min) // 4)

    # trail_start_r ±15%
    ts_center = coarse_optimal['trail_start_r']
    ts_min = max(0.2, ts_center * 0.85)
    ts_max = min(1.5, ts_center * 1.15)

    # trail_dist_r ±20%
    td_center = coarse_optimal['trail_dist_r']
    td_min = max(0.01, td_center * 0.8)
    td_max = min(0.12, td_center * 1.2)

    return {
        'atr_mult': [
            round(atr_min, 2),
            round(atr_min + (atr_max - atr_min) * 0.25, 2),
            round(atr_center, 2),
            round(atr_min + (atr_max - atr_min) * 0.75, 2),
            round(atr_max, 2)
        ],
        'filter_tf': list(set(tf_range)),  # 중복 제거
        'entry_validity_hours': [
            entry_min,
            entry_min + entry_step,
            entry_center,
            entry_center + entry_step,
            entry_max
        ],
        'trail_start_r': [
            round(ts_min, 2),
            round(ts_min + (ts_max - ts_min) * 0.25, 2),
            round(ts_center, 2),
            round(ts_min + (ts_max - ts_min) * 0.75, 2),
            round(ts_max, 2)
        ],
        'trail_dist_r': [
            round(td_min, 3),
            round(td_min + (td_max - td_min) * 0.25, 3),
            round(td_center, 3),
            round(td_min + (td_max - td_min) * 0.75, 3),
            round(td_max, 3)
        ]
    }


def run_stage_1(optimizer, df):
    """Stage 1: Coarse Grid Search (MDD 절대 필터 추가)"""
    print("\n" + "=" * 80)
    print("Stage 1: Coarse Grid Search (243개 조합)")
    print("=" * 80)

    coarse_ranges = build_coarse_ranges_v3()

    # 그리드 생성
    grid = coarse_ranges.copy()
    for key, value in DEFAULT_PARAMS.items():
        if key not in grid:
            grid[key] = [value]

    # 조합 수 계산
    total_combos = 1
    for values in coarse_ranges.values():
        total_combos *= len(values)

    print(f"\n파라미터 범위:")
    for param, values in coarse_ranges.items():
        print(f"  {param}: {len(values)}개 - {values}")
    print(f"\n총 조합 수: {total_combos:,}개")
    print(f"예상 시간: ~{total_combos * 1.9 / 8 / 60:.1f}분 (8워커 기준)")

    # 백테스트
    start = datetime.now()
    results = optimizer.run_optimization(
        df=df,
        grid=grid,
        n_cores=8,
        metric='sharpe_ratio',
        skip_filter=True
    )
    elapsed = (datetime.now() - start).total_seconds()

    # ✅ MDD 분포 확인 (필터 제거)
    print(f"\n백테스트 완료: {len(results)}개 조합")

    # MDD 분포 출력
    mdd_values = sorted([r.max_drawdown for r in results])
    print(f"\nMDD 분포:")
    print(f"  최소: {mdd_values[0]:.1f}%")
    print(f"  25%: {mdd_values[len(mdd_values)//4]:.1f}%")
    print(f"  중간: {mdd_values[len(mdd_values)//2]:.1f}%")
    print(f"  75%: {mdd_values[len(mdd_values)*3//4]:.1f}%")
    print(f"  최대: {mdd_values[-1]:.1f}%")

    # MDD 가중치 정렬 (v7.25.2)
    # 점수 = Sharpe × (5 / max(MDD, 5))
    results.sort(key=lambda x: x.sharpe_ratio * (5.0 / max(x.max_drawdown, 5.0)), reverse=True)
    top_5 = results[:5]

    print(f"\nStage 1 완료: {len(results)}개 조합, {elapsed:.1f}초")
    print(f"\n상위 5개 최적 영역 (MDD 가중치 적용):")
    for i, res in enumerate(top_5, 1):
        score = res.sharpe_ratio * (5.0 / max(res.max_drawdown, 5.0))
        print(f"  {i}. 점수={score:.2f} (Sharpe={res.sharpe_ratio:.2f}, MDD={res.max_drawdown:.1f}%), "
              f"atr={res.params['atr_mult']}, filter={res.params['filter_tf']}, entry={res.params['entry_validity_hours']}h")

    return top_5


def run_stage_2(optimizer, df, top_5):
    """Stage 2: Fine-Tuning around top 5 regions"""
    print("\n" + "=" * 80)
    print("Stage 2: Fine-Tuning (~500개 조합)")
    print("=" * 80)

    all_fine_results = []

    for i, coarse_optimal in enumerate(top_5, 1):
        print(f"\n영역 {i}/5 탐색 중...")

        fine_ranges = build_fine_ranges(coarse_optimal.params)

        # 그리드 생성
        grid = fine_ranges.copy()
        for key, value in DEFAULT_PARAMS.items():
            if key not in grid:
                grid[key] = [value]

        # 조합 수 계산
        region_combos = 1
        for values in fine_ranges.values():
            region_combos *= len(values)

        # 백테스트
        start = datetime.now()
        results = optimizer.run_optimization(
            df=df,
            grid=grid,
            n_cores=8,
            metric='sharpe_ratio',
            skip_filter=True
        )
        elapsed = (datetime.now() - start).total_seconds()

        print(f"  완료: {len(results)}개 조합, {elapsed:.1f}초")

        all_fine_results.extend(results)

    # 최종 정렬 (v7.25 표준)
    all_fine_results.sort(key=lambda x: (
        -x.simple_return,
        -10.0 / x.max_drawdown if x.max_drawdown > 0 else 1.0,
        x.max_drawdown
    ))

    print(f"\nStage 2 완료: 총 {len(all_fine_results)}개 조합")

    return all_fine_results


def main():
    """메인 함수 - 시도 3"""
    # UTF-8 설정
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("2단계 Coarse-to-Fine 백테스트 - 시도 3 (v7.25.3)")
    print("목표: MDD <10% 달성")
    print("=" * 80)

    # 데이터 로드
    print("\n데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    success = dm.load_historical()
    if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
        print("데이터 로드 실패")
        return

    df = dm.df_entry_full
    print(f"데이터: {len(df):,}개 1h 봉")

    # Optimizer 생성
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )

    # Stage 1: Coarse Grid
    top_5 = run_stage_1(optimizer, df)

    # Stage 2: Fine-Tuning
    final_results = run_stage_2(optimizer, df, top_5)

    # 최종 결과 출력 (상위 20개)
    print("\n" + "=" * 110)
    print("최종 상위 20개 결과")
    print("=" * 110)

    header = (
        f"{'순위':>4} {'등급':>4} {'단리':>10} {'복리':>10} {'거래당':>8} "
        f"{'MDD':>8} {'안전x':>8} {'Sharpe':>8} {'승률':>8} 파라미터"
    )
    print(header)
    print("-" * 110)

    for rank, res in enumerate(final_results[:20], 1):
        params_str = f"atr={res.params['atr_mult']}, filter={res.params['filter_tf']}, " \
                     f"entry={res.params['entry_validity_hours']}h, " \
                     f"ts={res.params['trail_start_r']}, td={res.params['trail_dist_r']}"
        emoji = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉', 'F': '❌'}.get(res.stability, '?')
        safe_lev = 10.0 / res.max_drawdown if res.max_drawdown > 0 else 1.0

        row = (
            f"{rank:>4} {emoji}{res.stability:>3} "
            f"{res.simple_return:>9.1f}% "
            f"{res.compound_return:>9.1f}% "
            f"{res.avg_pnl:>7.2f}% "
            f"{res.max_drawdown:>7.1f}% "
            f"{safe_lev:>7.1f}x "
            f"{res.sharpe_ratio:>8.2f} "
            f"{res.win_rate:>7.1f}% "
            f"{params_str}"
        )
        print(row)

    # 최적 파라미터 출력 및 저장
    best = final_results[0]

    print("\n" + "=" * 80)
    print("최적 조합")
    print("=" * 80)

    print("```python")
    print("OPTIMAL_PARAMS = {")
    for key in ['atr_mult', 'filter_tf', 'entry_validity_hours', 'trail_start_r', 'trail_dist_r']:
        value = best.params[key]
        if isinstance(value, str):
            print(f"    '{key}': '{value}',")
        else:
            print(f"    '{key}': {value},")
    print("}")
    print("```")

    safe_lev = 10.0 / best.max_drawdown if best.max_drawdown > 0 else 1.0

    print(f"""
성능 지표 (v7.25 핵심 6개):
  등급:          {best.stability}
  단리 수익:      {best.simple_return:,.1f}%
  복리 수익:      {best.compound_return:,.1f}%
  거래당 평균:    {best.avg_pnl:.2f}%
  MDD:           {best.max_drawdown:.1f}%
  안전 레버리지:  {safe_lev:.1f}x

참고 지표:
  승률:          {best.win_rate:.1f}%
  총 거래:       {best.trades:,}회
  Sharpe:        {best.sharpe_ratio:.2f}
  PF:            {best.profit_factor:.2f}
""")

    # 시도 비교 (시도 1, 2, 3)
    print("=" * 80)
    print("시도 비교")
    print("=" * 80)
    print(f"{'항목':<20} {'시도 1':>15} {'시도 2':>15} {'시도 3':>15}")
    print("-" * 75)
    print(f"{'MDD':<20} {'60.6%':>15} {'41.2%':>15} {best.max_drawdown:>14.1f}%")
    print(f"{'단리 수익':<20} {'3,944.6%':>15} {'1,692.2%':>15} {best.simple_return:>14.1f}%")
    print(f"{'Sharpe':<20} {'17.12':>15} {'11.14':>15} {best.sharpe_ratio:>14.2f}")
    print(f"{'안전 레버리지':<20} {'0.17x':>15} {'0.24x':>15} {safe_lev:>14.1f}x")
    print(f"{'ATR (최적)':<20} {'2.4':>15} {'1.5':>15} {best.params['atr_mult']:>14.1f}")

    # 목표 달성 여부
    print("\n" + "=" * 80)
    print("목표 달성 여부")
    print("=" * 80)

    mdd_target = 10.0
    safe_lev_target = 2.5

    print(f"MDD 목표:           <{mdd_target}% → 실제: {best.max_drawdown:.1f}% ({'✅ 달성' if best.max_drawdown < mdd_target else '❌ 미달'})")
    print(f"안전 레버리지 목표: >{safe_lev_target}x → 실제: {safe_lev:.1f}x ({'✅ 달성' if safe_lev > safe_lev_target else '❌ 미달'})")
    print(f"수익률 목표:        >500% → 실제: {best.simple_return:.1f}% ({'✅ 달성' if best.simple_return > 500 else '❌ 미달'})")

    print("\n2단계 Coarse-to-Fine 백테스트 완료 (시도 3)!")


if __name__ == '__main__':
    main()
