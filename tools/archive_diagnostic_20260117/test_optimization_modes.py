"""
최적화 모드별 성능 테스트
=======================

퀵/스탠다드/딥 모드의 성능과 결과 품질을 비교합니다.
"""

import sys
import os
from pathlib import Path
import time
import pandas as pd

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.optimizer import (
    generate_grid_by_mode,
    estimate_combinations,
    get_worker_info,
    BacktestOptimizer
)
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def test_mode(
    mode: str,
    symbol: str = 'BTCUSDT',
    exchange: str = 'bybit',
    tf: str = '1h'
) -> dict:
    """
    모드별 최적화 실행 및 성능 측정

    Args:
        mode: 'quick', 'standard', 'deep'
        symbol: 심볼
        exchange: 거래소
        tf: 타임프레임

    Returns:
        결과 딕셔너리
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"모드 테스트: {mode.upper()}")
    logger.info(f"{'='*80}")

    # 데이터 로드
    logger.info(f"데이터 로딩: {exchange} {symbol}")
    dm = BotDataManager(exchange, symbol)

    if not dm.load_historical():
        logger.error("데이터 로드 실패")
        return {'success': False, 'error': '데이터 로드 실패'}

    df = dm.df_entry_full
    if df is None or len(df) == 0:
        logger.error("데이터가 비어 있습니다")
        return {'success': False, 'error': '데이터 없음'}

    logger.info(f"데이터 기간: {df.index[0]} ~ {df.index[-1]} ({len(df):,}개)")

    # 그리드 생성
    grid = generate_grid_by_mode(tf, mode)
    total_combinations, estimated_minutes = estimate_combinations(grid)

    # CPU 정보
    worker_info = get_worker_info(mode)

    logger.info(f"\n그리드 정보:")
    logger.info(f"  예상 조합 수: {total_combinations:,}개")
    logger.info(f"  예상 시간: {estimated_minutes:.1f}분")
    logger.info(f"\nCPU 정보:")
    logger.info(f"  총 코어: {worker_info['total_cores']}")
    logger.info(f"  사용 워커: {worker_info['workers']} ({worker_info['usage_percent']:.0f}%)")
    logger.info(f"  여유 코어: {worker_info['free_cores']}")
    logger.info(f"  설명: {worker_info['description']}")

    # 최적화 실행
    logger.info(f"\n최적화 시작...")
    opt = BacktestOptimizer(AlphaX7Core, df)

    start_time = time.time()

    try:
        results = opt.run_optimization(df, grid)
        elapsed = time.time() - start_time

        # 결과 분석
        if results and len(results) > 0:
            best = results[0]

            logger.info(f"\n{'='*80}")
            logger.info(f"✅ 최적화 완료")
            logger.info(f"{'='*80}")
            logger.info(f"실행 시간: {elapsed:.1f}초 ({elapsed/60:.2f}분)")
            logger.info(f"실제 조합 수: {len(results):,}개")
            logger.info(f"조합당 시간: {elapsed/len(results):.3f}초")
            logger.info(f"\n최고 성과:")
            logger.info(f"  승률: {best.win_rate:.2f}%")
            logger.info(f"  수익률: {best.total_return:.2f}%")
            logger.info(f"  MDD: {best.max_drawdown:.2f}%")
            logger.info(f"  Sharpe: {best.sharpe_ratio:.2f}")
            logger.info(f"  거래 수: {best.trades}회")

            # 상위 5개 결과
            logger.info(f"\n상위 5개 결과:")
            for i, r in enumerate(results[:5], 1):
                logger.info(
                    f"  {i}. 승률 {r.win_rate:.1f}% | "
                    f"수익 {r.total_return:.1f}% | "
                    f"MDD {r.max_drawdown:.1f}% | "
                    f"거래 {r.trades}회"
                )

            return {
                'success': True,
                'mode': mode,
                'elapsed_seconds': elapsed,
                'elapsed_minutes': elapsed / 60,
                'combinations': len(results),
                'estimated_combinations': total_combinations,
                'time_per_combination': elapsed / len(results) if len(results) > 0 else 0,
                'best_win_rate': best.win_rate,
                'best_return': best.total_return,
                'best_mdd': best.max_drawdown,
                'best_sharpe': best.sharpe_ratio,
                'best_trades': best.trades,
                'top5_avg_win_rate': sum(r.win_rate for r in results[:5]) / 5,
                'top5_avg_return': sum(r.total_return for r in results[:5]) / 5,
            }

        else:
            logger.error("최적화 결과 없음")
            return {
                'success': False,
                'mode': mode,
                'elapsed_seconds': elapsed,
                'error': '결과 없음'
            }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"최적화 실패: {e}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'mode': mode,
            'elapsed_seconds': elapsed,
            'error': str(e)
        }


def compare_modes(symbol: str = 'BTCUSDT', exchange: str = 'bybit', tf: str = '1h'):
    """
    3가지 모드 비교 실행

    Args:
        symbol: 심볼
        exchange: 거래소
        tf: 타임프레임
    """
    logger.info(f"\n{'#'*80}")
    logger.info(f"최적화 모드 비교 테스트")
    logger.info(f"{'#'*80}")
    logger.info(f"심볼: {exchange} {symbol}")
    logger.info(f"타임프레임: {tf}")
    logger.info(f"{'#'*80}\n")

    modes = ['quick', 'standard', 'deep']
    results = {}

    for mode in modes:
        result = test_mode(mode, symbol, exchange, tf)
        results[mode] = result

        # 각 모드 사이에 잠시 대기 (시스템 안정화)
        if mode != modes[-1]:
            logger.info("\n5초 대기 중...")
            time.sleep(5)

    # 비교 리포트
    logger.info(f"\n{'='*80}")
    logger.info(f"비교 리포트")
    logger.info(f"{'='*80}\n")

    # 성공한 모드만 비교
    success_results = {k: v for k, v in results.items() if v.get('success')}

    if not success_results:
        logger.error("모든 모드 실패")
        return

    # 테이블 형식으로 출력
    logger.info(f"{'모드':<12} {'시간(분)':<12} {'조합 수':<12} {'승률(%)':<12} {'수익(%)':<12} {'MDD(%)':<12}")
    logger.info(f"{'-'*80}")

    for mode in ['quick', 'standard', 'deep']:
        if mode in success_results:
            r = success_results[mode]
            logger.info(
                f"{mode.upper():<12} "
                f"{r['elapsed_minutes']:<12.2f} "
                f"{r['combinations']:<12,} "
                f"{r['best_win_rate']:<12.2f} "
                f"{r['best_return']:<12.2f} "
                f"{r['best_mdd']:<12.2f}"
            )

    # 속도 비교
    if 'quick' in success_results and 'standard' in success_results:
        speedup_std = success_results['quick']['elapsed_minutes'] / success_results['standard']['elapsed_minutes']
        logger.info(f"\nQuick vs Standard 속도: {speedup_std:.1f}배 빠름")

    if 'quick' in success_results and 'deep' in success_results:
        speedup_deep = success_results['quick']['elapsed_minutes'] / success_results['deep']['elapsed_minutes']
        logger.info(f"Quick vs Deep 속도: {speedup_deep:.1f}배 빠름")

    # 품질 비교
    logger.info(f"\n품질 비교 (승률 기준):")
    best_mode = max(success_results.items(), key=lambda x: x[1]['best_win_rate'])
    logger.info(f"  최고 승률: {best_mode[0].upper()} ({best_mode[1]['best_win_rate']:.2f}%)")

    logger.info(f"\n품질 비교 (수익률 기준):")
    best_return = max(success_results.items(), key=lambda x: x[1]['best_return'])
    logger.info(f"  최고 수익: {best_return[0].upper()} ({best_return[1]['best_return']:.2f}%)")

    # CSV 저장
    output_dir = project_root / 'docs'
    output_dir.mkdir(exist_ok=True)

    df_results = pd.DataFrame([
        {
            'mode': k.upper(),
            'elapsed_minutes': v['elapsed_minutes'],
            'combinations': v['combinations'],
            'win_rate': v['best_win_rate'],
            'return': v['best_return'],
            'mdd': v['best_mdd'],
            'sharpe': v['best_sharpe'],
            'trades': v['best_trades'],
        }
        for k, v in success_results.items()
    ])

    csv_path = output_dir / 'optimization_modes_comparison.csv'
    df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"\n결과 저장: {csv_path}")

    logger.info(f"\n{'='*80}")
    logger.info(f"테스트 완료")
    logger.info(f"{'='*80}\n")


if __name__ == '__main__':
    # 기본 테스트
    compare_modes('BTCUSDT', 'bybit', '1h')
