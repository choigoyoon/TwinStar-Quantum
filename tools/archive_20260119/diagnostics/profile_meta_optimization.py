"""메타 최적화 성능 프로파일링 스크립트

병목 지점 분석:
1. 백테스트 실행 시간
2. 데이터 로딩/전송 오버헤드
3. ProcessPool 워커 효율성
4. CPU 코어 활용률

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import time
import cProfile
import pstats
import io
import multiprocessing
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Optional

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


def profile_meta_optimization(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h',
    sample_size: int = 100,  # 작은 샘플로 테스트
    max_iterations: int = 1
):
    """메타 최적화 프로파일링

    Args:
        exchange: 거래소명
        symbol: 심볼
        timeframe: 타임프레임
        sample_size: 샘플 크기 (작게 시작)
        max_iterations: 반복 횟수
    """
    print("=" * 80)
    print("메타 최적화 성능 프로파일링")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1/5] 데이터 로드 중...")
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

    print(f"✅ 데이터 로드: {len(df)} 캔들, {load_time:.2f}초")

    # 2. Optimizer 생성
    print("\n[2/5] Optimizer 생성 중...")
    from core.strategy_core import AlphaX7Core
    from core.optimizer import BacktestOptimizer

    setup_start = time.time()
    base_optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )
    setup_time = time.time() - setup_start
    print(f"✅ Optimizer 생성: {setup_time:.2f}초")

    # 3. MetaOptimizer 생성
    print("\n[3/5] MetaOptimizer 생성 중...")
    from core.meta_optimizer import MetaOptimizer

    meta = MetaOptimizer(
        base_optimizer=base_optimizer,
        sample_size=sample_size,
        min_improvement=0.05,
        max_iterations=max_iterations
    )
    print(f"✅ MetaOptimizer 생성")

    # 4. CPU 정보 출력
    print("\n[4/5] CPU 정보")
    cpu_count = multiprocessing.cpu_count()
    print(f"  - 총 CPU 코어: {cpu_count}")
    print(f"  - 사용 예정 워커: {cpu_count - 1}")

    # 5. 프로파일링 실행
    print("\n[5/5] 메타 최적화 프로파일링 시작...")
    print(f"  - 샘플 크기: {sample_size}")
    print(f"  - 반복 횟수: {max_iterations}")
    print(f"  - 총 백테스트 수: {sample_size * max_iterations}")

    # cProfile로 프로파일링
    profiler = cProfile.Profile()
    profiler.enable()

    start_time = time.time()
    result = meta.run_meta_optimization(
        df=df,
        trend_tf=timeframe,
        metric='sharpe_ratio'
    )
    elapsed = time.time() - start_time

    profiler.disable()

    # 6. 결과 분석
    print("\n" + "=" * 80)
    print("프로파일링 결과")
    print("=" * 80)

    print(f"\n총 실행 시간: {elapsed:.2f}초")
    print(f"반복 횟수: {result['iterations']}")
    print(f"테스트 조합 수: {result['statistics']['total_combinations_tested']}")
    print(f"조합당 평균 시간: {elapsed / result['statistics']['total_combinations_tested'] * 1000:.2f}ms")

    if result['best_result']:
        print(f"\n최고 성과:")
        print(f"  - Sharpe Ratio: {result['best_result'].sharpe_ratio:.2f}")
        print(f"  - Win Rate: {result['best_result'].win_rate:.1f}%")
        print(f"  - Trades: {result['best_result'].trades}")

    # 7. 함수별 시간 통계
    print("\n" + "=" * 80)
    print("함수별 실행 시간 (상위 20개)")
    print("=" * 80)

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)

    lines = s.getvalue().split('\n')
    for line in lines[:25]:  # 헤더 + 상위 20개
        print(line)

    # 8. 병목 분석
    print("\n" + "=" * 80)
    print("병목 분석")
    print("=" * 80)

    # 총 시간 분해
    components = {
        '데이터 로드': load_time,
        'Optimizer 생성': setup_time,
        '메타 최적화': elapsed
    }

    total = sum(components.values())

    print("\n시간 구성:")
    for name, duration in components.items():
        pct = (duration / total) * 100
        print(f"  {name:20s}: {duration:8.2f}초 ({pct:5.1f}%)")

    # 이론적 최대 처리량
    theoretical_throughput = cpu_count * (1000 / (elapsed / sample_size))
    print(f"\n이론적 최대 처리량: {theoretical_throughput:.0f} 백테스트/초")
    print(f"실제 처리량: {sample_size / elapsed:.0f} 백테스트/초")
    print(f"워커 효율성: {(sample_size / elapsed) / theoretical_throughput * 100:.1f}%")

    # 9. 권장사항
    print("\n" + "=" * 80)
    print("성능 개선 권장사항")
    print("=" * 80)

    avg_time_per_bt = (elapsed / sample_size) * 1000  # ms

    print(f"\n백테스트 1개당 평균 시간: {avg_time_per_bt:.2f}ms")

    if avg_time_per_bt > 100:
        print("⚠️ 백테스트 속도가 느립니다 (>100ms)")
        print("  - 전략 로직 최적화 필요")
        print("  - 지표 계산 캐싱 검토")
    elif avg_time_per_bt > 50:
        print("⚠️ 백테스트 속도가 평범합니다 (50-100ms)")
        print("  - 벡터화 최적화 검토")
    else:
        print("✅ 백테스트 속도 양호 (<50ms)")

    worker_efficiency = (sample_size / elapsed) / theoretical_throughput * 100

    if worker_efficiency < 50:
        print("\n⚠️ 워커 효율성이 낮습니다 (<50%)")
        print("  - ProcessPool 오버헤드 큼")
        print("  - 데이터 직렬화 비용 높음")
        print("  - 작업 단위 크기 조정 필요")
    elif worker_efficiency < 75:
        print("\n⚠️ 워커 효율성이 보통입니다 (50-75%)")
        print("  - 병렬화 개선 여지 있음")
    else:
        print("\n✅ 워커 효율성 양호 (>75%)")

    # 10. 프로파일 데이터 저장
    print("\n" + "=" * 80)
    print("프로파일 데이터 저장")
    print("=" * 80)

    profile_dir = Path('tools/profiles')
    profile_dir.mkdir(exist_ok=True)

    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    profile_file = profile_dir / f"meta_opt_{timestamp}.prof"

    profiler.dump_stats(str(profile_file))
    print(f"✅ 프로파일 저장: {profile_file}")

    # 텍스트 리포트 저장
    report_file = profile_dir / f"meta_opt_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("메타 최적화 프로파일링 리포트\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"거래소: {exchange}\n")
        f.write(f"심볼: {symbol}\n")
        f.write(f"타임프레임: {timeframe}\n")
        f.write(f"샘플 크기: {sample_size}\n")
        f.write(f"반복 횟수: {max_iterations}\n\n")

        f.write(f"총 실행 시간: {elapsed:.2f}초\n")
        f.write(f"백테스트 1개당 평균: {avg_time_per_bt:.2f}ms\n")
        f.write(f"워커 효율성: {worker_efficiency:.1f}%\n\n")

        f.write("=" * 80 + "\n")
        f.write("함수별 실행 시간 (상위 50개)\n")
        f.write("=" * 80 + "\n\n")

        s2 = io.StringIO()
        ps2 = pstats.Stats(profiler, stream=s2).sort_stats('cumulative')
        ps2.print_stats(50)
        f.write(s2.getvalue())

    print(f"✅ 텍스트 리포트 저장: {report_file}")

    print("\n" + "=" * 80)
    print("프로파일링 완료")
    print("=" * 80)

    return result


def benchmark_single_backtest(df: pd.DataFrame, runs: int = 10):
    """단일 백테스트 벤치마크

    Args:
        df: 데이터프레임
        runs: 실행 횟수
    """
    print("\n" + "=" * 80)
    print("단일 백테스트 벤치마크")
    print("=" * 80)

    from core.strategy_core import AlphaX7Core
    from config.parameters import DEFAULT_PARAMS

    strategy = AlphaX7Core(use_mtf=True)

    times = []

    for i in range(runs):
        start = time.time()

        trades = strategy.run_backtest(
            df_pattern=df,
            df_entry=df,
            slippage=0.0005,
            **DEFAULT_PARAMS
        )

        elapsed = time.time() - start
        times.append(elapsed)

        print(f"  Run {i+1}/{runs}: {elapsed*1000:.2f}ms ({len(trades) if trades else 0} trades)")

    avg_time = np.mean(times) * 1000
    std_time = np.std(times) * 1000
    min_time = np.min(times) * 1000
    max_time = np.max(times) * 1000

    print(f"\n통계:")
    print(f"  평균: {avg_time:.2f}ms")
    print(f"  표준편차: {std_time:.2f}ms")
    print(f"  최소: {min_time:.2f}ms")
    print(f"  최대: {max_time:.2f}ms")

    return avg_time


if __name__ == '__main__':
    import sys

    # 기본값
    exchange = 'bybit'
    symbol = 'BTCUSDT'
    timeframe = '1h'
    sample_size = 100
    max_iterations = 1

    # 명령줄 인자 처리
    if len(sys.argv) > 1:
        sample_size = int(sys.argv[1])
    if len(sys.argv) > 2:
        max_iterations = int(sys.argv[2])

    # 1. 단일 백테스트 벤치마크
    from core.data_manager import BotDataManager

    dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
    if dm.load_historical() and dm.df_entry_full is not None:
        benchmark_single_backtest(dm.df_entry_full, runs=10)

    # 2. 메타 최적화 프로파일링
    profile_meta_optimization(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        sample_size=sample_size,
        max_iterations=max_iterations
    )

    print("\n" + "=" * 80)
    print("프로파일링 스크립트 실행 완료")
    print("=" * 80)
    print("\n권장 분석 도구:")
    print("  1. SnakeViz (시각화): snakeviz tools/profiles/meta_opt_<timestamp>.prof")
    print("  2. gprof2dot (그래프): gprof2dot -f pstats tools/profiles/meta_opt_<timestamp>.prof | dot -Tpng -o output.png")
    print("  3. PyCharm Profiler: Open .prof file in PyCharm")
