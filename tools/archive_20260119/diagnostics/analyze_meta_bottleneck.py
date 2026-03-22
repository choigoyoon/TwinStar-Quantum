"""메타 최적화 병목 간단 분석

실행 시간 측정 및 병목 지점 파악

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import multiprocessing
import pandas as pd
import numpy as np
from typing import Dict, List

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


def analyze_bottleneck(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h',
    sample_sizes: List[int] = [10, 50, 100]
):
    """병목 분석

    Args:
        exchange: 거래소명
        symbol: 심볼
        timeframe: 타임프레임
        sample_sizes: 테스트할 샘플 크기 리스트
    """
    print("=" * 80)
    print("메타 최적화 병목 분석")
    print("=" * 80)

    # CPU 정보
    cpu_count = multiprocessing.cpu_count()
    print(f"\nCPU 정보:")
    print(f"  총 코어 수: {cpu_count}")
    print(f"  사용 예정 워커: {cpu_count - 1}")

    # 데이터 로드
    print(f"\n데이터 로드 중... ({exchange} {symbol})")
    from core.data_manager import BotDataManager

    dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})

    load_start = time.time()
    if not dm.load_historical():
        print("❌ 데이터 로드 실패")
        return
    load_time = time.time() - load_start

    df = dm.df_entry_full
    if df is None:
        print("❌ 데이터가 없습니다")
        return

    print(f"✅ 데이터 로드 완료: {len(df)} 캔들, {load_time:.2f}초")

    # Optimizer 생성
    from core.strategy_core import AlphaX7Core
    from core.optimizer import BacktestOptimizer

    base_optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )

    # MetaOptimizer 생성
    from core.meta_optimizer import MetaOptimizer

    results: List[Dict] = []

    # 샘플 크기별 테스트
    for sample_size in sample_sizes:
        print("\n" + "-" * 80)
        print(f"샘플 크기: {sample_size}")
        print("-" * 80)

        meta = MetaOptimizer(
            base_optimizer=base_optimizer,
            sample_size=sample_size,
            min_improvement=0.05,
            max_iterations=1  # 1회만 테스트
        )

        # 실행 시간 측정
        start_time = time.time()

        result = meta.run_meta_optimization(
            df=df,
            trend_tf=timeframe,
            metric='sharpe_ratio'
        )

        elapsed = time.time() - start_time

        # 통계 수집
        stats = {
            'sample_size': sample_size,
            'elapsed': elapsed,
            'combinations_tested': result['statistics']['total_combinations_tested'],
            'avg_time_per_combo': (elapsed / result['statistics']['total_combinations_tested']) * 1000,  # ms
            'throughput': result['statistics']['total_combinations_tested'] / elapsed,  # combos/sec
            'best_sharpe': result['best_result'].sharpe_ratio if result['best_result'] else 0,
            'iterations': result['iterations']
        }

        results.append(stats)

        # 결과 출력
        print(f"  총 시간: {elapsed:.2f}초")
        print(f"  테스트 조합: {stats['combinations_tested']}")
        print(f"  조합당 평균: {stats['avg_time_per_combo']:.2f}ms")
        print(f"  처리량: {stats['throughput']:.1f} 조합/초")
        print(f"  최고 Sharpe: {stats['best_sharpe']:.2f}")

    # 종합 분석
    print("\n" + "=" * 80)
    print("종합 분석")
    print("=" * 80)

    # 표 형식 출력
    print("\n샘플 크기별 성능:")
    print(f"{'샘플':>8} {'시간(초)':>10} {'조합수':>8} {'평균(ms)':>10} {'처리량':>12} {'Sharpe':>8}")
    print("-" * 68)

    for stat in results:
        print(
            f"{stat['sample_size']:>8} "
            f"{stat['elapsed']:>10.2f} "
            f"{stat['combinations_tested']:>8} "
            f"{stat['avg_time_per_combo']:>10.2f} "
            f"{stat['throughput']:>12.1f} "
            f"{stat['best_sharpe']:>8.2f}"
        )

    # 선형성 분석
    print("\n선형성 분석:")

    if len(results) >= 2:
        # 샘플 크기 대비 시간 증가율
        first = results[0]
        last = results[-1]

        size_ratio = last['sample_size'] / first['sample_size']
        time_ratio = last['elapsed'] / first['elapsed']

        print(f"  샘플 크기 증가: {first['sample_size']} → {last['sample_size']} ({size_ratio:.1f}배)")
        print(f"  시간 증가: {first['elapsed']:.2f}초 → {last['elapsed']:.2f}초 ({time_ratio:.1f}배)")

        if abs(time_ratio - size_ratio) / size_ratio < 0.1:
            print("  ✅ 선형 확장성 양호 (오차 <10%)")
        elif abs(time_ratio - size_ratio) / size_ratio < 0.3:
            print("  ⚠️ 선형 확장성 보통 (오차 10-30%)")
        else:
            print("  ❌ 선형 확장성 나쁨 (오차 >30%)")
            print("  → 오버헤드가 큼 (ProcessPool 직렬화, 데이터 전송 등)")

    # 1000개 샘플 예상 시간
    if results:
        avg_time_per_combo = np.mean([r['avg_time_per_combo'] for r in results])
        estimated_1000 = (1000 * avg_time_per_combo) / 1000  # 초

        print(f"\n1000개 샘플 예상 시간:")
        print(f"  {estimated_1000:.1f}초 (약 {estimated_1000/60:.1f}분)")

        # CPU 활용률 추정
        theoretical_max = cpu_count * (1000 / avg_time_per_combo)  # 조합/초
        actual_throughput = np.mean([r['throughput'] for r in results])
        cpu_efficiency = (actual_throughput / theoretical_max) * 100

        print(f"\nCPU 활용률 추정:")
        print(f"  이론적 최대: {theoretical_max:.1f} 조합/초")
        print(f"  실제 처리량: {actual_throughput:.1f} 조합/초")
        print(f"  워커 효율성: {cpu_efficiency:.1f}%")

    # 병목 지점 추정
    print("\n" + "=" * 80)
    print("병목 지점 추정")
    print("=" * 80)

    if results:
        avg_time = np.mean([r['avg_time_per_combo'] for r in results])

        print(f"\n백테스트 1개당 평균 시간: {avg_time:.2f}ms")

        # 시간 분해 추정
        print("\n예상 시간 구성:")

        # ProcessPool 오버헤드 (직렬화/역직렬화)
        overhead_pct = 100 - cpu_efficiency if 'cpu_efficiency' in locals() else 30
        overhead_ms = avg_time * (overhead_pct / 100)

        print(f"  백테스트 순수 실행: {avg_time - overhead_ms:.2f}ms ({100-overhead_pct:.1f}%)")
        print(f"  ProcessPool 오버헤드: {overhead_ms:.2f}ms ({overhead_pct:.1f}%)")

        # 개선 방안
        print("\n개선 방안:")

        if overhead_ms > avg_time * 0.3:
            print("  1. ProcessPool 오버헤드 감소")
            print("     - 데이터 직렬화 최소화 (공유 메모리 사용)")
            print("     - 작업 단위 크기 증가 (배치 처리)")
            print("     - ThreadPool 고려 (GIL 허용 시)")

        if avg_time > 50:
            print("  2. 백테스트 로직 최적화")
            print("     - 벡터화 (NumPy 활용)")
            print("     - 지표 계산 캐싱")
            print("     - 불필요한 계산 제거")

        if cpu_efficiency < 70:
            print("  3. 병렬화 효율 개선")
            print("     - 워커 수 조정")
            print("     - 작업 분배 알고리즘 개선")

    # 결과 저장
    print("\n" + "=" * 80)
    print("결과 저장")
    print("=" * 80)

    from pathlib import Path

    output_dir = Path('tools/analysis')
    output_dir.mkdir(exist_ok=True)

    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    csv_file = output_dir / f"bottleneck_analysis_{timestamp}.csv"

    df_results = pd.DataFrame(results)
    df_results.to_csv(csv_file, index=False)

    print(f"✅ CSV 저장: {csv_file}")

    # 텍스트 리포트
    txt_file = output_dir / f"bottleneck_analysis_{timestamp}.txt"

    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("메타 최적화 병목 분석 리포트\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"거래소: {exchange}\n")
        f.write(f"심볼: {symbol}\n")
        f.write(f"타임프레임: {timeframe}\n")
        f.write(f"CPU 코어: {cpu_count}\n\n")

        f.write("샘플 크기별 성능:\n")
        f.write(f"{'샘플':>8} {'시간(초)':>10} {'조합수':>8} {'평균(ms)':>10} {'처리량':>12} {'Sharpe':>8}\n")
        f.write("-" * 68 + "\n")

        for stat in results:
            f.write(
                f"{stat['sample_size']:>8} "
                f"{stat['elapsed']:>10.2f} "
                f"{stat['combinations_tested']:>8} "
                f"{stat['avg_time_per_combo']:>10.2f} "
                f"{stat['throughput']:>12.1f} "
                f"{stat['best_sharpe']:>8.2f}\n"
            )

        if results:
            avg_time = np.mean([r['avg_time_per_combo'] for r in results])
            f.write(f"\n평균 시간/조합: {avg_time:.2f}ms\n")

            estimated_1000 = (1000 * avg_time) / 1000
            f.write(f"1000개 샘플 예상 시간: {estimated_1000:.1f}초 ({estimated_1000/60:.1f}분)\n")

    print(f"✅ 텍스트 리포트 저장: {txt_file}")

    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)

    return results


if __name__ == '__main__':
    import sys

    # 명령줄 인자
    exchange = sys.argv[1] if len(sys.argv) > 1 else 'bybit'
    symbol = sys.argv[2] if len(sys.argv) > 2 else 'BTCUSDT'
    timeframe = sys.argv[3] if len(sys.argv) > 3 else '1h'

    # 샘플 크기 (점진적 증가)
    sample_sizes = [10, 50, 100]

    analyze_bottleneck(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        sample_sizes=sample_sizes
    )

    print("\n다음 단계:")
    print("  1. 더 큰 샘플 테스트: python tools/analyze_meta_bottleneck.py bybit BTCUSDT 1h")
    print("  2. 프로파일링 실행: python tools/profile_meta_optimization.py 100 1")
    print("  3. CPU 활용률 모니터링: 작업 관리자 또는 htop")
