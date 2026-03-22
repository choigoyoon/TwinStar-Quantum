"""메타 최적화 실제 데이터 테스트

Bybit BTC/USDT 15분봉 데이터 (상장 시기부터)로 메타 최적화 실행

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# UTF-8 출력 설정 (Windows용)
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    """메타 최적화 테스트 메인 함수"""
    print("=" * 80)
    print("메타 최적화 실제 데이터 테스트")
    print("=" * 80)
    print()

    # 1. 데이터 로드
    print("1. 데이터 로드 중...")
    from core.data_manager import BotDataManager

    dm = BotDataManager(
        exchange_name='bybit',
        symbol='BTCUSDT',
        strategy_params={'entry_tf': '15m'}
    )

    start_time = time.time()
    if not dm.load_historical():
        print("❌ 데이터 로드 실패")
        return

    df = dm.df_entry_full
    load_time = time.time() - start_time

    if df is None or df.empty:
        print("❌ 데이터가 비어있습니다")
        return

    print(f"✅ 데이터 로드 완료: {len(df):,}개 캔들")
    print(f"   기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"   로드 시간: {load_time:.2f}초")
    print()

    # 2. BacktestOptimizer 생성
    print("2. BacktestOptimizer 생성 중...")
    from core.optimizer import BacktestOptimizer
    from core.strategy_core import AlphaX7Core

    base_optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )
    print("✅ BacktestOptimizer 생성 완료")
    print()

    # 3. MetaOptimizer 생성
    print("3. MetaOptimizer 생성 중...")
    from dev_future.optimization_modes.meta_optimizer import MetaOptimizer

    meta_optimizer = MetaOptimizer(
        base_optimizer=base_optimizer,
        sample_size=100,  # 빠른 테스트: 1000 → 100
        min_improvement=0.05,
        max_iterations=2  # 빠른 테스트: 3 → 2
    )
    print("✅ MetaOptimizer 생성 완료")
    print(f"   샘플 크기: 100개/iteration (빠른 테스트)")
    print(f"   최대 반복: 2회")
    print(f"   수렴 기준: 개선율 <5%")
    print()

    # 4. 메타 최적화 실행
    print("4. 메타 최적화 실행 중...")
    print("-" * 80)

    def progress_callback(event: str, *args):
        """진행 상황 콜백"""
        if event == 'iteration_started':
            iteration, sample_size = args
            print(f"\n🔍 Iteration {iteration}: {sample_size:,}개 조합 테스트 중...")

        elif event == 'iteration_finished':
            iteration, result_count, best_score = args
            print(f"✅ Iteration {iteration} 완료:")
            print(f"   결과 수: {result_count:,}개")
            print(f"   최고 점수 (Sharpe): {best_score:.4f}")

    start_time = time.time()
    result = meta_optimizer.run_meta_optimization(
        df=df,
        trend_tf='15m',
        metric='sharpe_ratio',
        callback=progress_callback
    )
    elapsed = time.time() - start_time

    print()
    print("-" * 80)
    print("✅ 메타 최적화 완료!")
    print()

    # 5. 결과 출력
    print("5. 결과 요약")
    print("=" * 80)

    print(f"\n📊 실행 통계:")
    print(f"   반복 횟수: {result['iterations']}")
    print(f"   수렴 이유: {result['convergence_reason']}")
    print(f"   총 조합 수: {result['statistics']['total_combinations_tested']:,}개")
    print(f"   실행 시간: {elapsed:.1f}초")

    print(f"\n🏆 최고 결과:")
    best = result['best_result']
    print(f"   Sharpe Ratio: {best.sharpe_ratio:.4f}")
    print(f"   Win Rate: {best.win_rate:.2f}%")
    print(f"   Profit Factor: {best.profit_factor:.2f}")
    print(f"   MDD: {best.max_drawdown:.2f}%")
    print(f"   Total Return: {best.total_return:.2f}%")
    print(f"   Total Trades: {best.trades}")

    print(f"\n📈 점수 히스토리:")
    for i, score in enumerate(result['statistics']['top_score_history'], 1):
        if i > 1:
            prev = result['statistics']['top_score_history'][i-2]
            improvement = (score - prev) / prev * 100
            print(f"   Iteration {i}: {score:.4f} (개선율: {improvement:+.2f}%)")
        else:
            print(f"   Iteration {i}: {score:.4f}")

    print(f"\n🎯 추출된 범위 (atr_mult 예시):")
    atr_ranges = result['extracted_ranges'].get('atr_mult', {})
    if atr_ranges:
        print(f"   Quick: {atr_ranges.get('quick', [])}")
        print(f"   Standard: {atr_ranges.get('standard', [])}")
        print(f"   Deep: {atr_ranges.get('deep', [])}")

    # 6. JSON 저장
    print()
    print("6. 결과 저장 중...")
    filepath = meta_optimizer.save_meta_ranges('bybit', 'BTCUSDT', '15m')
    print(f"✅ 저장 완료: {filepath}")

    # 7. 성능 평가
    print()
    print("7. 성능 평가")
    print("=" * 80)

    target_time = 20.0
    actual_time = elapsed
    efficiency = (target_time / actual_time * 100) if actual_time > 0 else 0

    print(f"   목표 시간: {target_time:.1f}초")
    print(f"   실제 시간: {actual_time:.1f}초")
    print(f"   효율성: {efficiency:.1f}%")

    if actual_time <= target_time:
        print("   ✅ 목표 달성!")
    else:
        print(f"   ⚠️ 목표 초과 ({actual_time - target_time:.1f}초)")

    print()
    print("=" * 80)
    print("테스트 완료!")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
