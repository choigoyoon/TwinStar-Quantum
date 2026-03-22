#!/usr/bin/env python3
"""중요 파라미터 정밀 탐색 (Fine-Tuning) - v7.25

Phase 1 영향도 분석 결과를 바탕으로
상위 3개 중요 파라미터를 촘촘하게 탐색

리팩토링 (2026-01-18):
- ParamOptimizer 재사용 (tools/optimize_params.py)
- 중복 코드 제거 (~150줄 감소)
- SSOT 준수 (config.parameters 활용)

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.parameters import FINE_TUNING_RANGES, DEFAULT_PARAMS
from core.data_manager import BotDataManager


def main():
    """메인 함수"""
    # Windows 콘솔 UTF-8 인코딩 설정
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("🎯 정밀 탐색 (Fine-Tuning) 테스트 - v7.25")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n📥 데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 로드 실패")
            return

        df = dm.df_entry_full
        print(f"✅ 데이터: {len(df):,}개 1h 봉")
        if 'timestamp' in df.columns:
            print(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

    except Exception as e:
        print(f"❌ 데이터 로드 에러: {e}")
        return

    # 2. Phase 1 결과 (영향도 분석)
    print("\n" + "=" * 80)
    print("📌 Phase 1 결과 (영향도 분석)")
    print("=" * 80)
    print("1. filter_tf:      +4.01 영향 ⭐⭐⭐⭐⭐")
    print("2. trail_start_r:  +3.51 영향 ⭐⭐⭐⭐⭐")
    print("3. trail_dist_r:   +2.47 영향 ⭐⭐⭐⭐")

    # 3. 정밀 탐색 범위 (SSOT)
    top_params = ['filter_tf', 'trail_start_r', 'trail_dist_r']
    fine_ranges = FINE_TUNING_RANGES

    print(f"\n🔧 FINE_TUNING_RANGES (config.parameters):")
    for param in top_params:
        print(f"   {param}: {len(fine_ranges[param])}개 - {fine_ranges[param]}")

    # 타임프레임 검증
    from config.parameters import validate_tf_hierarchy
    entry_tf = '1h'

    print(f"\n🔍 타임프레임 계층 검증: entry_tf='{entry_tf}'")
    for ftf in fine_ranges['filter_tf']:
        is_valid = validate_tf_hierarchy(entry_tf, ftf)
        assert is_valid, f"❌ filter_tf '{ftf}' must be > entry_tf '{entry_tf}'"
    print(f"✅ TF hierarchy validated: {fine_ranges['filter_tf']}")

    total_combinations = (
        len(fine_ranges['filter_tf']) *
        len(fine_ranges['trail_start_r']) *
        len(fine_ranges['trail_dist_r'])
    )
    print(f"\n총 조합 수: {total_combinations:,}개")
    print(f"예상 시간: {total_combinations * 0.7 / 8 / 60:.1f}분 (8워커 기준)")

    # 4. ParamOptimizer로 실행 (중복 코드 제거)
    print("\n" + "=" * 80)
    print("🚀 ParamOptimizer 실행")
    print("=" * 80)

    start_time = datetime.now()

    # ParamOptimizer는 내부적으로 PARAM_RANGES를 사용
    # FINE_TUNING_RANGES를 사용하려면 직접 BacktestOptimizer 호출 필요
    # → 간단한 방법: optimize_params.py의 ParamOptimizer 클래스를 임시로 수정하지 않고
    #    여기서 직접 BacktestOptimizer 사용

    from core.optimizer import BacktestOptimizer
    from core.strategy_core import AlphaX7Core

    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )

    # Grid 생성 (고정 파라미터 포함)
    grid = fine_ranges.copy()
    for key, value in DEFAULT_PARAMS.items():
        if key not in grid:
            grid[key] = [value]

    # 병렬 실행
    print("⚡ 병렬 백테스트 시작...")
    backtest_results = optimizer.run_optimization(
        df=df,
        grid=grid,
        n_cores=8,
        metric='sharpe_ratio',
        skip_filter=True
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    # 5. 결과 변환 (v7.25 표준)
    results = []
    for br in backtest_results:
        key_params = {k: br.params[k] for k in top_params}

        result_dict = {
            'params': key_params,
            'simple_return': br.simple_return,
            'compound_return': br.compound_return,
            'avg_pnl': br.avg_pnl,
            'mdd': br.max_drawdown,
            'safe_leverage': 10.0 / br.max_drawdown if br.max_drawdown > 0 else 1.0,
            'sharpe_ratio': br.sharpe_ratio,
            'win_rate': br.win_rate,
            'total_trades': br.trades,
            'pf': br.profit_factor,
            'grade': br.stability
        }
        results.append(result_dict)

    # v7.25 정렬
    results.sort(key=lambda x: (
        -x['simple_return'],
        -x['safe_leverage'],
        x['mdd']
    ))

    # 6. 결과 출력
    print("\n" + "=" * 110)
    print(f"🏆 상위 20개 결과 (v7.25 표준)")
    print("=" * 110)

    header = (
        f"{'순위':>4} {'등급':>4} {'단리':>10} {'복리':>10} {'거래당':>8} "
        f"{'MDD':>8} {'안전x':>8} {'Sharpe':>8} {'승률':>8} 파라미터"
    )
    print(header)
    print("-" * 110)

    for rank, result in enumerate(results[:20], 1):
        params_str = ', '.join(f"{k}={v}" for k, v in result['params'].items())
        emoji = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉', 'F': '❌'}.get(result['grade'], '?')

        row = (
            f"{rank:>4} {emoji}{result['grade']:>3} "
            f"{result['simple_return']:>9.1f}% "
            f"{result['compound_return']:>9.1f}% "
            f"{result['avg_pnl']:>7.2f}% "
            f"{result['mdd']:>7.1f}% "
            f"{result['safe_leverage']:>7.1f}x "
            f"{result['sharpe_ratio']:>8.2f} "
            f"{result['win_rate']:>7.1f}% "
            f"{params_str}"
        )
        print(row)

    # 최적 조합 상세
    best = results[0]

    print("\n" + "=" * 80)
    print("🎯 최적 조합")
    print("=" * 80)

    print("```python")
    print("OPTIMAL_PARAMS = {")
    for key, value in sorted(best['params'].items()):
        if isinstance(value, str):
            print(f"    '{key}': '{value}',")
        else:
            print(f"    '{key}': {value},")
    print("}")
    print("```")

    print(f"""
성능 지표 (v7.25 핵심 6개):
  등급:          {best['grade']}
  단리 수익:      {best['simple_return']:,.1f}%
  복리 수익:      {best['compound_return']:,.1f}%
  거래당 평균:    {best['avg_pnl']:.2f}%
  MDD:           {best['mdd']:.1f}%
  안전 레버리지:  {best['safe_leverage']:.1f}x

참고 지표:
  승률:          {best['win_rate']:.1f}%
  총 거래:       {best['total_trades']:,}회
  Sharpe:        {best['sharpe_ratio']:.2f}
  PF:            {best['pf']:.2f}
""")

    # 7. 성능 통계
    print("=" * 80)
    print("⏱️ 성능 통계")
    print("=" * 80)
    print(f"총 조합 수: {len(results):,}개")
    print(f"소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"평균 속도: {elapsed/len(results):.3f}초/조합")

    # 8. 개선도 분석
    print("\n" + "=" * 80)
    print("📈 개선도 분석 (v7.25 표준)")
    print("=" * 80)

    baseline_sharpe = 19.82  # Phase 1 기준점
    sharpe_improvement = best['sharpe_ratio'] - baseline_sharpe

    print(f"{'지표':<20} {'Baseline':>15} {'최적':>15} {'개선':>15}")
    print("-" * 70)
    print(f"{'Sharpe Ratio':<20} {baseline_sharpe:>14.2f} {best['sharpe_ratio']:>14.2f} {sharpe_improvement:>14.2f} ({sharpe_improvement/baseline_sharpe*100:+.1f}%)")
    print(f"{'단리 수익':<20} {'N/A':>15} {best['simple_return']:>14.2f}% {'신규':>15}")
    print(f"{'복리 수익':<20} {'N/A':>15} {best['compound_return']:>14.2f}% {'신규':>15}")
    print(f"{'거래당 평균':<20} {'N/A':>15} {best['avg_pnl']:>14.2f}% {'신규':>15}")
    print(f"{'MDD':<20} {'N/A':>15} {best['mdd']:>14.2f}% {'신규':>15}")
    print(f"{'안전 레버리지':<20} {'N/A':>15} {best['safe_leverage']:>14.1f}x {'신규':>15}")

    # 9. 프리셋 저장 (선택 사항)
    print("\n" + "=" * 80)
    print("💾 프리셋 저장")
    print("=" * 80)

    save_preset = input("최적 파라미터를 프리셋으로 저장하시겠습니까? (y/N): ").strip().lower()

    if save_preset == 'y':
        # 전체 파라미터 조합
        full_params = DEFAULT_PARAMS.copy()
        full_params.update(best['params'])

        # 프리셋 저장
        from utils.preset_storage import PresetStorage
        storage = PresetStorage()

        try:
            filepath = storage.save_preset(
                symbol='BTCUSDT',
                tf='1h',
                params=full_params,
                optimization_result={
                    'win_rate': best['win_rate'],
                    'mdd': best['mdd'],
                    'sharpe_ratio': best['sharpe_ratio'],
                    'profit_factor': best['pf'],
                    'total_trades': best['total_trades'],
                    'total_pnl': best['simple_return'],
                    'compound_return': best['compound_return'],
                    'avg_pnl': best['avg_pnl'],
                    'stability': best['grade'],
                    'safe_leverage': best['safe_leverage'],
                },
                mode='fine_tuning_v7.25',
                strategy_type='macd',
                exchange='bybit'
            )
            print(f"✅ 프리셋 저장 완료: {filepath}")
        except Exception as e:
            print(f"❌ 프리셋 저장 실패: {e}")
    else:
        print("프리셋 저장 생략")

    print("\n✅ Fine-Tuning 테스트 완료!")


if __name__ == '__main__':
    main()
