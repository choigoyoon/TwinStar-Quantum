#!/usr/bin/env python3
"""Coarse-to-Fine 최적화 실행 스크립트 (v7.28)

Author: Claude Sonnet 4.5
Date: 2026-01-20
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.coarse_to_fine_optimizer import CoarseToFineOptimizer
from core.data_manager import BotDataManager
from utils.logger import get_module_logger
import pandas as pd

logger = get_module_logger(__name__)


def main():
    """메인 함수"""
    # 데이터 로드
    logger.info("데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    success = dm.load_historical()

    if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
        logger.error("ERROR: 데이터 로드 실패")
        return

    # 15분봉 → 1시간봉 리샘플링
    df_15m = dm.df_entry_full.copy()

    if 'timestamp' not in df_15m.columns:
        df_15m.reset_index(inplace=True)

    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_temp = df_15m.set_index('timestamp')

    df = df_temp.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    df.reset_index(inplace=True)

    # 2020-01-01 이후 필터링
    df = df[df['timestamp'] >= '2020-01-01'].copy()

    logger.info(f"OK 데이터:")
    logger.info(f"   15분봉: {len(df_15m):,}개")
    logger.info(f"   1시간봉: {len(df):,}개 (2020년 이후)")

    start_date = df['timestamp'].iloc[0]
    end_date = df['timestamp'].iloc[-1]
    total_days = (end_date - start_date).days
    logger.info(f"   기간: {start_date} ~ {end_date}")
    logger.info(f"   일수: {total_days:,}일")

    # Coarse-to-Fine 최적화 실행
    optimizer = CoarseToFineOptimizer(df, strategy_type='macd')
    result = optimizer.run(n_cores=8, save_csv=True)

    # 결과 출력
    logger.info("\n" + "=" * 110)
    logger.info("최적화 완료")
    logger.info("=" * 110)

    logger.info(f"총 조합 수: {result.total_combinations}개")
    logger.info(f"소요 시간: {result.elapsed_seconds:.1f}초 ({result.elapsed_seconds/60:.1f}분)")

    if result.csv_path:
        logger.info(f"결과 저장: {result.csv_path}")

    # 상위 15개 출력
    logger.info("\n" + "=" * 110)
    logger.info("상위 15개 결과 (Sharpe 순)")
    logger.info("=" * 110)
    logger.info(f"{'순위':>4} {'등급':>4} {'Sharpe':>8} {'승률':>7} {'MDD':>7} {'PnL':>9} "
                f"{'거래':>6} {'PF':>6} 파라미터")
    logger.info("-" * 110)

    for i, r in enumerate(result.stage2_results[:15], 1):
        params_str = ', '.join(f"{k}={v}" for k, v in sorted(r.params.items()))
        logger.info(f"{i:>4} {r.grade:>4} {r.sharpe_ratio:>8.2f} {r.win_rate:>6.1f}% "
                   f"{abs(r.max_drawdown):>6.1f}% {r.total_return:>8.1f}% {r.trades:>6} "
                   f"{r.profit_factor:>6.2f} {params_str}")

    # 최적 조합
    if result.stage2_results:
        best = result.stage2_results[0]
        logger.info("\n" + "=" * 70)
        logger.info("최적 조합 (v7.28)")
        logger.info("=" * 70)
        logger.info("```python")
        logger.info("OPTIMAL_PARAMS = {")
        for k in ['atr_mult', 'filter_tf', 'entry_validity_hours', 'trail_start_r', 'trail_dist_r']:
            v = best.params.get(k)
            if isinstance(v, str):
                logger.info(f"    '{k}': '{v}',")
            else:
                logger.info(f"    '{k}': {v},")
        logger.info("}")
        logger.info("```")

        safe_lev = 10.0 / abs(best.max_drawdown) if best.max_drawdown != 0 else 1.0
        safe_lev = min(safe_lev, 20.0)

        logger.info(f"\n등급: {best.grade} | Sharpe: {best.sharpe_ratio:.2f} | 승률: {best.win_rate:.1f}%")
        logger.info(f"MDD: {abs(best.max_drawdown):.1f}% | PnL: {best.total_return:.1f}% | 거래: {best.trades}회")
        logger.info(f"PF: {best.profit_factor:.2f} | 안전 레버리지: {safe_lev:.1f}x")

    logger.info("\n완료!")


if __name__ == '__main__':
    main()
