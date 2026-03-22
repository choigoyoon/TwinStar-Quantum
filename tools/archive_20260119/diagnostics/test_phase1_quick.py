"""Phase 1 Quick Test - v7.25 메트릭 통합 검증

8개 조합만 테스트하여 Phase 1 출력 형식 확인

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS


def print_results(results: list, top_n: int = 20):
    """결과 출력 (v7.25 표준)"""
    print("\n" + "=" * 110)
    print(f"🏆 상위 {min(top_n, len(results))}개 결과 (v7.25 표준)")
    print("=" * 110)

    header = (
        f"{'순위':>4} {'등급':>4} {'단리':>10} {'복리':>10} {'거래당':>8} "
        f"{'MDD':>8} {'안전x':>8} {'Sharpe':>8} {'승률':>8} 파라미터"
    )
    print(header)
    print("-" * 110)

    for rank, result in enumerate(results[:top_n], 1):
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


def main():
    """Quick Test: 8개 조합만 테스트"""
    print("=" * 60)
    print("🧪 Phase 1 Quick Test - v7.25 메트릭 통합")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n📥 데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 없음.")
            return

        df = dm.df_entry_full
        print(f"✅ 데이터 로드 완료: {len(df)}개 캔들")

    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    # 2. 소규모 파라미터 범위 정의 (8개 조합)
    top_params = ['filter_tf', 'trail_start_r']

    quick_ranges = {
        'filter_tf': ['4h', '12h'],           # 2개
        'trail_start_r': [0.4, 0.7, 1.0, 1.2], # 4개
    }

    total_combinations = 2 * 4  # 8개
    print(f"\n총 조합 수: {total_combinations}개")
    print(f"예상 시간: {total_combinations * 3.2 / 8 / 60:.1f}분")

    # 3. 최적화 실행
    start_time = datetime.now()

    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )

    # Grid 생성 (고정 파라미터 포함)
    grid = quick_ranges.copy()
    for key, value in DEFAULT_PARAMS.items():
        if key not in grid:
            grid[key] = [value]

    # 병렬 실행
    backtest_results = optimizer.run_optimization(
        df=df,
        grid=grid,
        n_cores=8,
        metric='sharpe_ratio',
        skip_filter=True
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    # 4. 결과 변환 (v7.25 표준)
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
            'grade': br.stability
        }
        results.append(result_dict)

    # 정렬 (v7.25: 단리 → 안전 레버리지 → MDD)
    results.sort(key=lambda x: (-x['simple_return'], -x['safe_leverage'], x['mdd']))

    # 5. 결과 출력 (상위 8개 전부)
    print_results(results, top_n=8)

    # 5. 성능 통계
    print("\n" + "=" * 60)
    print("⏱️ 성능 통계")
    print("=" * 60)
    print(f"총 조합 수: {len(results)}개")
    print(f"소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print(f"평균 속도: {elapsed/len(results):.3f}초/조합")

    # 6. v7.25 메트릭 검증
    print("\n" + "=" * 60)
    print("✅ v7.25 메트릭 검증")
    print("=" * 60)

    best = results[0]

    # 필수 필드 확인
    required_fields = [
        'params', 'simple_return', 'compound_return', 'avg_pnl',
        'mdd', 'safe_leverage', 'sharpe_ratio', 'win_rate',
        'total_trades', 'grade'
    ]

    missing_fields = [f for f in required_fields if f not in best]
    if missing_fields:
        print(f"❌ 누락된 필드: {missing_fields}")
    else:
        print("✅ 모든 필드 존재 (10개)")

    # 값 범위 검증
    checks = []
    checks.append(("단리 수익", best['simple_return'] > 0, f"{best['simple_return']:.2f}% > 0"))
    checks.append(("복리 수익", best['compound_return'] > 0, f"{best['compound_return']:.2f}% > 0"))
    checks.append(("거래당 평균", 0 < best['avg_pnl'] < 10, f"0 < {best['avg_pnl']:.2f}% < 10"))
    checks.append(("MDD", 0 < best['mdd'] < 50, f"0 < {best['mdd']:.2f}% < 50"))
    checks.append(("안전 레버리지", best['safe_leverage'] > 0, f"{best['safe_leverage']:.1f}x > 0"))
    checks.append(("승률", 0 <= best['win_rate'] <= 100, f"0 <= {best['win_rate']:.2f}% <= 100"))
    checks.append(("거래 횟수", best['total_trades'] > 0, f"{best['total_trades']} > 0"))
    checks.append(("등급", best['grade'] in ['S', 'A', 'B', 'C', 'D', 'F', '⚠️'], f"'{best['grade']}'"))

    print("\n값 범위 검증:")
    for name, is_valid, desc in checks:
        status = "✅" if is_valid else "❌"
        print(f"  {status} {name}: {desc}")

    # 정렬 검증
    print("\n정렬 순서 검증:")
    if len(results) >= 2:
        first = results[0]
        second = results[1]

        # v7.25 정렬 기준: 단리 → 안전 레버리지 → MDD
        sort_key_first = (-first['simple_return'], -first['safe_leverage'], first['mdd'])
        sort_key_second = (-second['simple_return'], -second['safe_leverage'], second['mdd'])

        if sort_key_first <= sort_key_second:
            print("  ✅ v7.25 정렬 기준 적용 (단리 → 안전 레버리지 → MDD)")
        else:
            print("  ❌ 정렬 순서 오류")
    else:
        print("  ⚠️ 결과 2개 미만 (정렬 검증 불가)")

    print("\n✅ Phase 1 Quick Test 완료!")


if __name__ == '__main__':
    main()
