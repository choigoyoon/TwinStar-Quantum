"""
CLI 최적화 실행 + CSV 저장

사용법:
    # Deep 모드 (전체 탐색)
    python run_optimization_cli.py --exchange bybit --symbol BTCUSDT --timeframe 1h --mode deep

    # Standard 모드
    python run_optimization_cli.py --exchange bybit --symbol BTCUSDT --timeframe 1h --mode standard

    # Quick 모드
    python run_optimization_cli.py --exchange bybit --symbol BTCUSDT --timeframe 1h --mode quick

출력:
    1. CSV: data/optimization_results/bybit_BTCUSDT_1h_deep_20260116_143000.csv
    2. 자동 분석 및 adaptive_ranges.json 업데이트
"""

import sys
import argparse
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer, generate_grid_by_mode
from core.strategy_core import AlphaX7Core
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description='최적화 실행 + CSV 저장')
    parser.add_argument('--exchange', default='bybit', help='거래소 (기본: bybit)')
    parser.add_argument('--symbol', required=True, help='심볼 (예: BTCUSDT)')
    parser.add_argument('--timeframe', default='1h', help='타임프레임 (기본: 1h)')
    parser.add_argument('--mode', default='deep', choices=['quick', 'standard', 'deep'],
                       help='최적화 모드 (기본: deep)')
    parser.add_argument('--workers', type=int, help='워커 수 (기본: 자동)')
    parser.add_argument('--no-csv', action='store_true', help='CSV 저장 안 함')
    parser.add_argument('--no-analyze', action='store_true', help='자동 분석 안 함')

    args = parser.parse_args()

    # 1. 데이터 로드
    logger.info(f"데이터 로드: {args.exchange} {args.symbol} {args.timeframe}")
    dm = BotDataManager(args.exchange, args.symbol, {'entry_tf': args.timeframe})

    if not dm.load_historical():
        logger.error("데이터 로드 실패")
        return 1

    if dm.df_entry_full is None or dm.df_entry_full.empty:
        logger.error("데이터가 비어있습니다")
        return 1

    # 2. 그리드 생성
    logger.info(f"그리드 생성: {args.mode} 모드")
    grid = generate_grid_by_mode(args.timeframe, args.mode)

    # 3. 워커 수 결정
    if args.workers:
        workers = args.workers
    else:
        from core.optimizer import get_optimal_workers
        workers = get_optimal_workers(args.mode)

    logger.info(f"워커 수: {workers}")

    # 4. 조합 수 추정 (메모리 효율적)
    from core.optimizer import estimate_combinations
    combo_count, estimated_time = estimate_combinations(grid)
    logger.info(f"최적화 시작: ~{combo_count:,}개 조합 (예상 시간: {estimated_time:.1f}분)")

    optimizer = BacktestOptimizer(AlphaX7Core, dm.df_entry_full)

    results = optimizer.run_optimization(
        df=dm.df_entry_full,
        grid=grid,
        n_cores=workers,
        mode=args.mode
    )

    if not results:
        logger.error("최적화 결과 없음")
        return 1

    logger.info(f"최적화 완료: {len(results)}개 결과")

    # 5. CSV 저장
    csv_path = None
    if not args.no_csv:
        csv_path = optimizer.save_results_to_csv(
            args.exchange,
            args.symbol,
            args.timeframe,
            args.mode
        )
        print(f"\n✅ CSV 저장: {csv_path}")

    # 6. 자동 분석 (Deep 모드만)
    if not args.no_analyze and args.mode == 'deep' and csv_path:
        logger.info("자동 분석 시작...")
        import subprocess

        try:
            result = subprocess.run([
                sys.executable,
                'tools/analyze_deep_results.py',
                '--csv', csv_path,
                '--exchange', args.exchange,
                '--symbol', args.symbol,
                '--timeframe', args.timeframe
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print(result.stdout)
                print("\n✅ 분석 완료! adaptive_ranges.json 업데이트됨")
            else:
                logger.warning(f"분석 실패: {result.stderr}")
        except Exception as e:
            logger.warning(f"분석 중 오류: {e}")

    # 7. 상위 결과 출력
    print("\n" + "="*60)
    print("📊 상위 10개 결과")
    print("="*60)
    for i, r in enumerate(results[:10], 1):
        print(f"{i:2d}. 승률={r.win_rate:.1f}% PF={r.profit_factor:.2f} "
              f"MDD={r.max_drawdown:.1f}% Sharpe={r.sharpe_ratio:.2f}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
