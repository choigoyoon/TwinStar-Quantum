"""메타 최적화 백그라운드 워커 (QThread)

메타 최적화를 백그라운드 스레드에서 실행하는 워커 클래스입니다.

Author: Claude Sonnet 4.5
Version: 1.0.0
Date: 2026-01-17
"""

import logging
from typing import Optional, Dict, Callable, Any
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget
import pandas as pd

logger = logging.getLogger(__name__)


class MetaOptimizationWorker(QThread):
    """메타 최적화 백그라운드 워커

    메타 최적화를 백그라운드 스레드에서 실행하여 UI 블로킹을 방지합니다.

    Signals:
        iteration_started(int, int): 반복 시작 (반복 번호, 샘플 수)
        iteration_finished(int, int, float): 반복 완료 (반복 번호, 결과 수, 최고 점수)
        finished(dict): 메타 최적화 완료 (최종 결과)
        error(str): 에러 발생 (에러 메시지)

    Usage:
        >>> worker = MetaOptimizationWorker(
        ...     exchange='bybit',
        ...     symbol='BTCUSDT',
        ...     timeframe='1h',
        ...     callback=on_progress
        ... )
        >>> worker.iteration_started.connect(on_iteration_started)
        >>> worker.iteration_finished.connect(on_iteration_finished)
        >>> worker.finished.connect(on_finished)
        >>> worker.error.connect(on_error)
        >>> worker.start()
    """

    # Signals
    iteration_started = pyqtSignal(int, int)       # (반복 번호, 샘플 수)
    iteration_finished = pyqtSignal(int, int, float)  # (반복 번호, 결과 수, 최고 점수)
    finished = pyqtSignal(dict)                    # 최종 결과
    error = pyqtSignal(str)                        # 에러 메시지

    def __init__(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        sample_size: int = 1000,
        min_improvement: float = 0.05,
        max_iterations: int = 3,
        metric: str = 'sharpe_ratio',
        callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None
    ):
        """MetaOptimizationWorker 초기화

        Args:
            exchange: 거래소명 (예: 'bybit')
            symbol: 심볼명 (예: 'BTCUSDT')
            timeframe: 타임프레임 (예: '1h')
            sample_size: 반복당 샘플 수 (기본 1,000개)
            min_improvement: 수렴 기준 (기본 5%)
            max_iterations: 최대 반복 횟수 (기본 3회)
            metric: 최적화 지표 (기본 'sharpe_ratio')
            callback: 외부 콜백 함수 (event: str, *args)
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.sample_size = sample_size
        self.min_improvement = min_improvement
        self.max_iterations = max_iterations
        self.metric = metric
        self.callback = callback

        logger.debug(
            f"MetaOptimizationWorker 초기화: {exchange} {symbol} {timeframe}, "
            f"sample_size={sample_size}, max_iterations={max_iterations}"
        )

    def run(self):
        """메타 최적화 실행 (백그라운드 스레드)"""
        try:
            logger.info(f"🔍 메타 최적화 시작: {self.exchange} {self.symbol} {self.timeframe}")

            # 1. 데이터 로드
            df = self._load_data()

            # 2. BacktestOptimizer 생성
            from core.optimizer import BacktestOptimizer
            from core.strategy_core import AlphaX7Core

            base_optimizer = BacktestOptimizer(
                strategy_class=AlphaX7Core,
                df=df,
                strategy_type='macd'  # 메타 최적화는 MACD 전략 기준
            )

            # 3. MetaOptimizer 생성
            from core.meta_optimizer import MetaOptimizer

            meta_optimizer = MetaOptimizer(
                base_optimizer=base_optimizer,
                sample_size=self.sample_size,
                min_improvement=self.min_improvement,
                max_iterations=self.max_iterations
            )

            # 4. 메타 최적화 실행
            result = meta_optimizer.run_meta_optimization(
                df=df,
                trend_tf=self.timeframe,
                metric=self.metric,
                callback=self._emit_progress
            )

            logger.info(
                f"✅ 메타 최적화 완료: {result['iterations']} iterations, "
                f"reason={result['convergence_reason']}"
            )

            # 5. 결과 반환
            self.finished.emit(result)

        except Exception as e:
            logger.error(f"❌ 메타 최적화 에러: {e}", exc_info=True)
            self.error.emit(str(e))

    def _load_data(self) -> pd.DataFrame:
        """데이터 로드

        Returns:
            OHLCV 데이터프레임

        Raises:
            ValueError: 데이터 로드 실패
        """
        from core.data_manager import BotDataManager

        try:
            dm = BotDataManager(
                exchange_name=self.exchange,
                symbol=self.symbol,
                strategy_params={'entry_tf': self.timeframe}
            )

            # 데이터 로드
            if not dm.load_historical():
                raise ValueError(f"데이터 로드 실패: {self.exchange} {self.symbol}")

            df = dm.df_entry_full

            if df is None or df.empty:
                raise ValueError(f"데이터가 비어있습니다: {self.exchange} {self.symbol}")

            logger.info(f"  데이터 로드 완료: {len(df)} rows")

            return df

        except Exception as e:
            logger.error(f"  데이터 로드 에러: {e}")
            raise

    def _emit_progress(self, event: str, *args):
        """진행 상황 시그널 발생

        Args:
            event: 이벤트 타입 ('iteration_started' or 'iteration_finished')
            *args: 이벤트별 인자
        """
        try:
            if event == 'iteration_started':
                iteration, sample_size = args
                self.iteration_started.emit(iteration, sample_size)

            elif event == 'iteration_finished':
                iteration, result_count, best_score = args
                self.iteration_finished.emit(iteration, result_count, best_score)

            # 외부 콜백 호출
            if self.callback:
                self.callback(event, *args)

        except Exception as e:
            logger.warning(f"진행 상황 시그널 에러: {e}")


if __name__ == '__main__':
    # 테스트 실행
    print("=== MetaOptimizationWorker Test ===")
    print("This module requires PyQt6 application context.")
    print("Usage:")
    print("  from ui.widgets.optimization.meta_worker import MetaOptimizationWorker")
    print("  worker = MetaOptimizationWorker('bybit', 'BTCUSDT', '1h')")
    print("  worker.start()")
