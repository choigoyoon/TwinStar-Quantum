"""
Multi-Symbol Parameter Optimizer (v1.0)

목적: 여러 심볼에서 동시에 잘 작동하는 범용 파라미터 찾기

전략:
1. 여러 심볼 데이터 로드
2. 각 파라미터 조합으로 모든 심볼 백테스트
3. 심볼별 승률 평균 최대화
4. 범용 프리셋 저장
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime

# 프로젝트 루트 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS, PARAM_RANGES_BY_MODE
from config.constants import EXCHANGE_INFO
from utils.metrics import calculate_backtest_metrics
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


@dataclass
class MultiSymbolResult:
    """멀티 심볼 최적화 결과"""
    params: dict
    symbol_results: Dict[str, dict]  # 심볼별 결과
    avg_win_rate: float
    avg_sharpe: float
    avg_mdd: float
    avg_pnl: float
    total_trades: int
    score: float  # 종합 점수


class MultiSymbolOptimizer:
    """여러 심볼 동시 최적화"""

    def __init__(
        self,
        exchange: str = 'bybit',
        symbols: Optional[List[str]] = None,
        timeframe: str = '1h',
        mode: str = 'quick'  # 'quick', 'standard', 'deep'
    ):
        self.exchange = exchange
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        self.timeframe = timeframe
        self.mode = mode

        logger.info(f"Multi-Symbol Optimizer 초기화")
        logger.info(f"  Exchange: {exchange}")
        logger.info(f"  Symbols: {symbols}")
        logger.info(f"  Timeframe: {timeframe}")
        logger.info(f"  Mode: {mode}")

        # 데이터 로드
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self._load_all_data()

    def _load_all_data(self):
        """모든 심볼 데이터 로드"""
        logger.info("=" * 60)
        logger.info("데이터 로드 시작")

        for symbol in self.symbols:
            try:
                dm = BotDataManager(
                    exchange_name=self.exchange,
                    symbol=symbol,
                    strategy_params={'entry_tf': self.timeframe}
                )

                # 데이터 로드
                dm.load_historical()
                df = dm.df_entry_full

                if df is None:
                    logger.warning(f"  ⚠️ {symbol}: 데이터 없음")
                    continue

                df_copy = df.copy()

                if len(df_copy) < 1000:
                    logger.warning(f"  ⚠️ {symbol}: 데이터 부족 ({len(df_copy)}개)")
                    continue

                self.data_cache[symbol] = df_copy
                logger.info(f"  ✅ {symbol}: {len(df_copy):,}개 캔들 로드")

            except Exception as e:
                logger.error(f"  ❌ {symbol}: 로드 실패 - {e}")

        logger.info(f"데이터 로드 완료: {len(self.data_cache)}/{len(self.symbols)}개 심볼")
        logger.info("=" * 60)

    def _run_single_backtest(self, symbol: str, params: dict) -> Optional[dict]:
        """단일 심볼 백테스트"""
        df = self.data_cache.get(symbol)
        if df is None:
            return None

        try:
            # 전략 실행
            strategy = AlphaX7Core()

            result = strategy.run_backtest(
                df_entry=df,
                df_pattern=df,
                df_filter=df,
                params=params
            )

            if not result or 'trades' not in result:
                return None

            trades = result['trades']
            if len(trades) < 5:
                return None

            # 메트릭 계산
            metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

            return {
                'win_rate': metrics['win_rate'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'mdd': metrics['mdd'],
                'total_pnl': metrics['total_pnl'],
                'total_trades': metrics['total_trades']
            }

        except Exception as e:
            logger.error(f"    백테스트 실패 ({symbol}): {e}")
            return None

    def _evaluate_params(self, params: dict) -> Optional[MultiSymbolResult]:
        """파라미터 평가 (모든 심볼)"""
        symbol_results = {}

        for symbol in self.data_cache.keys():
            result = self._run_single_backtest(symbol, params)
            if result:
                symbol_results[symbol] = result

        if not symbol_results:
            return None

        # 평균 계산
        avg_win_rate = float(np.mean([r['win_rate'] for r in symbol_results.values()]))
        avg_sharpe = float(np.mean([r['sharpe_ratio'] for r in symbol_results.values()]))
        avg_mdd = float(np.mean([r['mdd'] for r in symbol_results.values()]))
        avg_pnl = float(np.mean([r['total_pnl'] for r in symbol_results.values()]))
        total_trades = sum([r['total_trades'] for r in symbol_results.values()])

        # 종합 점수 (승률 60% + Sharpe 40%)
        score = float(avg_win_rate * 0.6 + (avg_sharpe / 30.0) * 0.4)

        return MultiSymbolResult(
            params=params,
            symbol_results=symbol_results,
            avg_win_rate=avg_win_rate,
            avg_sharpe=avg_sharpe,
            avg_mdd=avg_mdd,
            avg_pnl=avg_pnl,
            total_trades=total_trades,
            score=score
        )

    def optimize(self) -> Optional[MultiSymbolResult]:
        """최적화 실행"""
        logger.info("=" * 60)
        logger.info("Multi-Symbol 최적화 시작")
        logger.info(f"  Mode: {self.mode}")

        # 파라미터 범위
        param_ranges = PARAM_RANGES_BY_MODE.get(self.mode, {})
        if not param_ranges:
            param_ranges = PARAM_RANGES_BY_MODE['quick']

        # 조합 생성
        from itertools import product

        atr_mults = param_ranges.get('atr_mult', [1.25, 2.0, 2.5])
        filter_tfs = param_ranges.get('filter_tf', ['4h', '12h', '1d'])
        trail_start_rs = param_ranges.get('trail_start_r', [0.8, 1.5, 2.5])
        trail_dist_rs = param_ranges.get('trail_dist_r', [0.03, 0.1, 0.15])
        entry_validities = param_ranges.get('entry_validity_hours', [6, 48, 96])

        combinations = list(product(
            atr_mults,
            filter_tfs,
            trail_start_rs,
            trail_dist_rs,
            entry_validities
        ))

        logger.info(f"  총 조합 수: {len(combinations):,}개")
        logger.info("=" * 60)

        # 최적화 실행
        best_result: Optional[MultiSymbolResult] = None
        best_score = -1

        for idx, combo in enumerate(combinations, 1):
            atr_mult, filter_tf, trail_start_r, trail_dist_r, entry_validity = combo

            params = DEFAULT_PARAMS.copy()
            params.update({
                'atr_mult': atr_mult,
                'filter_tf': filter_tf,
                'trail_start_r': trail_start_r,
                'trail_dist_r': trail_dist_r,
                'entry_validity_hours': entry_validity
            })

            # 진행 상황
            if idx % 10 == 0 or idx == 1:
                logger.info(f"[{idx}/{len(combinations)}] 테스트 중... (최고 점수: {best_score:.4f})")

            # 평가
            result = self._evaluate_params(params)
            if result and result.score > best_score:
                best_score = result.score
                best_result = result

                logger.info(f"  ✨ 신기록! 점수={result.score:.4f}, 승률={result.avg_win_rate:.1f}%, Sharpe={result.avg_sharpe:.2f}")

        logger.info("=" * 60)
        if best_result is not None:
            logger.info("최적화 완료")
            logger.info(f"  최종 점수: {best_result.score:.4f}")
            logger.info(f"  평균 승률: {best_result.avg_win_rate:.2f}%")
            logger.info(f"  평균 Sharpe: {best_result.avg_sharpe:.2f}")
            logger.info(f"  평균 MDD: {best_result.avg_mdd:.2f}%")
        else:
            logger.warning("최적화 실패: 유효한 결과 없음")
        logger.info("=" * 60)

        return best_result

    def save_preset(self, result: MultiSymbolResult, filename: Optional[str] = None):
        """프리셋 저장"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"universal_{self.exchange}_{self.timeframe}_{timestamp}.json"

        preset_path = ROOT / 'presets' / filename
        preset_path.parent.mkdir(parents=True, exist_ok=True)

        preset_data = {
            "meta_info": {
                "type": "universal_multi_symbol",
                "exchange": self.exchange,
                "timeframe": self.timeframe,
                "symbols": list(result.symbol_results.keys()),
                "optimization_mode": self.mode,
                "created_at": datetime.now().isoformat()
            },
            "best_params": result.params,
            "avg_metrics": {
                "avg_win_rate": result.avg_win_rate,
                "avg_sharpe_ratio": result.avg_sharpe,
                "avg_mdd": result.avg_mdd,
                "avg_pnl": result.avg_pnl,
                "total_trades": result.total_trades,
                "score": result.score
            },
            "symbol_results": result.symbol_results
        }

        import json
        with open(preset_path, 'w', encoding='utf-8') as f:
            json.dump(preset_data, f, indent=2, ensure_ascii=False)

        logger.info(f"프리셋 저장 완료: {preset_path}")
        return preset_path


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Multi-Symbol Parameter Optimizer')
    parser.add_argument('--exchange', default='bybit', help='거래소 (기본값: bybit)')
    parser.add_argument('--symbols', default='BTCUSDT,ETHUSDT,BNBUSDT', help='심볼 (쉼표 구분)')
    parser.add_argument('--timeframe', default='1h', help='타임프레임 (기본값: 1h)')
    parser.add_argument('--mode', default='quick', choices=['quick', 'standard', 'deep'], help='최적화 모드')
    parser.add_argument('--output', help='출력 파일명 (기본값: 자동 생성)')

    args = parser.parse_args()

    # 심볼 파싱
    symbols = [s.strip() for s in args.symbols.split(',')]

    # 최적화 실행
    optimizer = MultiSymbolOptimizer(
        exchange=args.exchange,
        symbols=symbols,
        timeframe=args.timeframe,
        mode=args.mode
    )

    result = optimizer.optimize()

    if result:
        # 프리셋 저장
        preset_path = optimizer.save_preset(result, args.output)

        print("\n" + "=" * 60)
        print("✅ 최적화 완료!")
        print("=" * 60)
        print(f"📊 결과:")
        print(f"  평균 승률: {result.avg_win_rate:.2f}%")
        print(f"  평균 Sharpe: {result.avg_sharpe:.2f}")
        print(f"  평균 MDD: {result.avg_mdd:.2f}%")
        print(f"  평균 PnL: {result.avg_pnl:.2f}%")
        print(f"  총 거래: {result.total_trades:,}회")
        print(f"\n📁 프리셋: {preset_path}")
        print("=" * 60)

        print("\n📊 심볼별 성능:")
        for symbol, metrics in result.symbol_results.items():
            print(f"  {symbol:12s}: 승률 {metrics['win_rate']:.1f}%, Sharpe {metrics['sharpe_ratio']:.2f}, MDD {metrics['mdd']:.2f}%")
    else:
        print("❌ 최적화 실패")


if __name__ == '__main__':
    main()
