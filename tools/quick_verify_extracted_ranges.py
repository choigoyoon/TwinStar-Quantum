"""추출 범위 검증 - 간단한 버전

메타 최적화 방식 그대로 사용하여 추출 범위 검증

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
import json
from typing import Dict, List
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# UTF-8 출력 설정 (Windows용)
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def _single_backtest(params: Dict, df):
    """단일 백테스트 실행 (메타 최적화 방식)"""
    from core.strategy_core import AlphaX7Core
    from core.optimizer import OptimizationResult
    from config.parameters import DEFAULT_PARAMS

    try:
        # 전략 인스턴스 생성
        strategy = AlphaX7Core(use_mtf=True)

        # 백테스트 실행
        trades = strategy.run_backtest(
            df_pattern=df,
            df_entry=df,
            slippage=0.0005,
            atr_mult=params.get('atr_mult', DEFAULT_PARAMS.get('atr_mult', 1.5)),
            trail_start_r=params.get('trail_start_r', DEFAULT_PARAMS.get('trail_start_r', 0.8)),
            trail_dist_r=params.get('trail_dist_r', DEFAULT_PARAMS.get('trail_dist_r', 0.02)),
            pattern_tolerance=params.get('pattern_tolerance', DEFAULT_PARAMS.get('pattern_tolerance', 0.03)),
            entry_validity_hours=params.get('entry_validity_hours', DEFAULT_PARAMS.get('entry_validity_hours', 24.0)),
            pullback_rsi_long=params.get('pullback_rsi_long', DEFAULT_PARAMS.get('pullback_rsi_long', 35)),
            pullback_rsi_short=params.get('pullback_rsi_short', DEFAULT_PARAMS.get('pullback_rsi_short', 65)),
            max_adds=params.get('max_adds', DEFAULT_PARAMS.get('max_adds', 1)),
            filter_tf=params.get('filter_tf', '4h'),
            rsi_period=params.get('rsi_period', DEFAULT_PARAMS.get('rsi_period', 14)),
            atr_period=params.get('atr_period', DEFAULT_PARAMS.get('atr_period', 14)),
            macd_fast=params.get('macd_fast', DEFAULT_PARAMS.get('macd_fast', 12)),
            macd_slow=params.get('macd_slow', DEFAULT_PARAMS.get('macd_slow', 26)),
            macd_signal=params.get('macd_signal', DEFAULT_PARAMS.get('macd_signal', 9)),
            ema_period=params.get('ema_period', DEFAULT_PARAMS.get('ema_period', 20)),
            enable_pullback=params.get('enable_pullback', False)
        )

        if not trades or len(trades) == 0:
            return None

        # 메트릭 계산
        from utils.metrics import calculate_backtest_metrics

        bt_metrics = calculate_backtest_metrics(
            trades=trades,
            leverage=params.get('leverage', 1),
            capital=100.0
        )

        # OptimizationResult 생성
        result = OptimizationResult(
            params=params,
            trades=bt_metrics.get('total_trades', 0),
            win_rate=bt_metrics.get('win_rate', 0),
            total_return=bt_metrics.get('total_pnl', 0),
            simple_return=bt_metrics.get('total_pnl', 0),
            compound_return=bt_metrics.get('total_pnl', 0),
            max_drawdown=bt_metrics.get('mdd', 0),
            sharpe_ratio=bt_metrics.get('sharpe_ratio', 0),
            profit_factor=bt_metrics.get('profit_factor', 0)
        )

        return result

    except Exception as e:
        logger.error(f"백테스트 실패: {e}")
        return None


def main():
    """메인 함수"""
    print("=" * 80)
    print("추출 범위 검증 - Quick 모드")
    print("=" * 80)
    print()

    # 1. 메타 최적화 결과 로드
    json_path = 'presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json'
    print(f"1. 메타 최적화 결과 로드 중...")
    print(f"   경로: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        meta_result = json.load(f)

    # Quick 모드 범위 추출
    raw_ranges = meta_result['param_ranges_by_mode']
    quick_ranges = {}
    for param, mode_dict in raw_ranges.items():
        quick_ranges[param] = mode_dict['quick']

    print("   ✅ 로드 완료")
    print()

    # 2. 데이터 로드
    print("2. 데이터 로드 중...")
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

    # 3. 조합 생성
    print("3. 조합 생성 중...")
    print(f"   Quick 범위:")
    for param, values in quick_ranges.items():
        print(f"     {param}: {values}")

    # 전체 조합
    all_combinations = list(itertools.product(*quick_ranges.values()))
    param_names = list(quick_ranges.keys())

    print(f"   → 총 조합 수: {len(all_combinations):,}개")
    print()

    # 4. 백테스트 실행
    print("4. 백테스트 실행 중...")
    print("-" * 80)

    import multiprocessing
    n_cores = max(1, multiprocessing.cpu_count() - 1)
    print(f"   CPU 코어: {n_cores}개 사용")
    print()

    results = []
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=n_cores) as executor:
        futures = {}

        for combo in all_combinations:
            # 조합을 딕셔너리로 변환
            params = dict(zip(param_names, combo))

            # 백테스트 작업 제출
            future = executor.submit(_single_backtest, params, df)
            futures[future] = params

        # 결과 수집
        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result()
                if result:
                    results.append(result)

                # 진행률 표시
                if completed % 10 == 0 or completed == len(all_combinations):
                    print(f"   진행: {completed}/{len(all_combinations)} ({completed/len(all_combinations)*100:.1f}%)")

            except Exception as e:
                logger.error(f"작업 실패: {e}")

    elapsed = time.time() - start_time

    print()
    print("-" * 80)
    print(f"✅ 백테스트 완료: {len(results)}/{len(all_combinations)}개 성공")
    print(f"   실행 시간: {elapsed:.1f}초")
    print()

    if not results:
        print("❌ 결과가 없습니다")
        return

    # 5. 결과 정렬
    print("5. 결과 정렬 중...")
    results.sort(key=lambda r: r.sharpe_ratio, reverse=True)
    print(f"✅ 정렬 완료")
    print()

    # 6. TOP 10 출력
    print("6. TOP 10 결과")
    print("=" * 80)
    print(f"{'순위':<5} {'Sharpe':<10} {'승률':<8} {'PF':<8} {'MDD':<8} {'거래수':<8}")
    print("-" * 80)

    for i, r in enumerate(results[:10], 1):
        print(
            f"{i:<5} "
            f"{r.sharpe_ratio:<10.2f} "
            f"{r.win_rate:<8.1f} "
            f"{r.profit_factor:<8.2f} "
            f"{r.max_drawdown:<8.2f} "
            f"{r.trades:<8}"
        )

    # 최고 결과 상세
    best = results[0]
    print(f"\n🥇 최고 결과 상세:")
    print("-" * 80)
    print(f"Sharpe Ratio: {best.sharpe_ratio:.4f}")
    print(f"Win Rate: {best.win_rate:.2f}%")
    print(f"Profit Factor: {best.profit_factor:.2f}")
    print(f"MDD: {best.max_drawdown:.2f}%")
    print(f"Total Return: {best.total_return:.2f}%")
    print(f"Total Trades: {best.trades}")

    print(f"\n⚙️ 최적 파라미터:")
    for key, value in best.params.items():
        print(f"  {key}: {value}")

    print()
    print("=" * 80)
    print("검증 완료!")
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
