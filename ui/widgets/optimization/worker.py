"""
ui/widgets/optimization/worker.py

최적화 백그라운드 워커 (QThread)

Zone A 마이그레이션:
    - GUI/optimization_widget.py에서 OptimizationWorker 추출
    - 타입 안전성 확보
    - 취소 기능 개선

타입 안전성 강화 (v7.12 - 2026-01-16)
"""

from typing import Optional, Any, List, Dict
from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd

from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class OptimizationWorker(QThread):
    """
    최적화 실행 백그라운드 워커

    Signals:
        progress(int, int): (완료 수, 전체 수)
        task_done(object): 개별 태스크 완료 (결과 딕셔너리)
        finished(list): 전체 완료 (결과 리스트)
        error(str): 에러 발생 (에러 메시지)

    Usage:
        from core.optimization_logic import OptimizationEngine

        engine = OptimizationEngine(...)
        worker = OptimizationWorker(
            engine=engine,
            df=df,
            param_grid={'atr_mult': [1.5, 2.0], 'rsi_period': [14, 21]},
            max_workers=4
        )
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()
    """

    # Signals
    progress = pyqtSignal(int, int)  # (completed, total)
    task_done = pyqtSignal(object)   # 단일 태스크 완료
    finished = pyqtSignal(list)      # 전체 완료
    error = pyqtSignal(str)          # 에러

    def __init__(
        self,
        engine: Any,  # OptimizationEngine (순환 import 방지)
        df: pd.DataFrame,
        param_grid: List[Dict[str, Any]],
        max_workers: int = 4,
        symbol: str = "",
        timeframe: str = "",
        capital_mode: str = "compound",
        strategy_type: str = "macd",
        parent: Optional[QThread] = None
    ):
        """
        Args:
            engine: OptimizationEngine 인스턴스
            df: 백테스트 데이터프레임
            param_grid: 파라미터 그리드 [{'atr_mult': 1.5, ...}, ...]
            max_workers: 최대 워커 수 (기본: 4)
            symbol: 심볼 (로깅용)
            timeframe: 타임프레임 (로깅용)
            capital_mode: 자본 모드 ('compound' or 'fixed')
            strategy_type: 전략 유형 ('macd' or 'adx') - v3.0
            parent: 부모 스레드
        """
        super().__init__(parent)
        self.engine = engine
        self.df = df
        self.param_grid = param_grid
        self.max_workers = max_workers
        self.symbol = symbol
        self.timeframe = timeframe
        self.capital_mode = capital_mode
        self.strategy_type = strategy_type
        self._cancelled = False

        logger.debug(
            f"OptimizationWorker 초기화: {symbol} {timeframe}, "
            f"max_workers={max_workers}, capital_mode={capital_mode}, strategy_type={strategy_type}"
        )
    
    def run(self):
        """최적화 실행 (백그라운드 스레드) - v7.26: BacktestOptimizer 사용"""
        try:
            logger.info(f"최적화 시작: {self.symbol} {self.timeframe}")

            # v7.26: BacktestOptimizer 직접 사용 (test_fine_tuning.py와 동일)
            from core.optimizer import BacktestOptimizer
            from core.strategy_core import AlphaX7Core

            optimizer = BacktestOptimizer(
                strategy_class=AlphaX7Core,
                df=self.df,
                strategy_type=self.strategy_type
            )

            # 파라미터 그리드를 Dict[str, List] 형식으로 변환
            # param_grid: [{'atr_mult': 1.5, 'filter_tf': '4h'}, ...]
            # → grid: {'atr_mult': [1.5, 2.0], 'filter_tf': ['4h', '6h']}
            grid: Dict[str, List[Any]] = {}
            for params in self.param_grid:
                for key, value in params.items():
                    if key not in grid:
                        grid[key] = []
                    if value not in grid[key]:
                        grid[key].append(value)

            logger.info(f"파라미터 그리드: {len(self.param_grid)}개 조합")
            for key, values in grid.items():
                logger.debug(f"  {key}: {len(values)}개 - {values}")

            # 진행률 콜백 설정 (v7.26.2)
            def progress_callback(completed: int, total: int):
                """진행 상황 업데이트 콜백"""  # [v7.26]
                self.progress.emit(completed, total)

            # 최적화 실행
            backtest_results = optimizer.run_optimization(
                df=self.df,
                grid=grid,
                n_cores=self.max_workers,
                metric='sharpe_ratio',
                skip_filter=True,  # MTF 필터 이미 적용됨
                progress_callback=progress_callback  # 진행률 콜백 연결
            )

            if self._cancelled:
                logger.info("최적화 취소됨")
                self.error.emit("사용자가 최적화를 취소했습니다.")
                return

            # 결과 변환: BacktestResult → UI용 딕셔너리
            results = []
            for br in backtest_results:
                # v7.25 표준 지표
                result_dict = {
                    'params': br.params,
                    'simple_return': br.simple_return,
                    'compound_return': br.compound_return,
                    'avg_pnl': br.avg_pnl,
                    'mdd': br.max_drawdown,
                    'safe_leverage': 10.0 / br.max_drawdown if br.max_drawdown > 0 else 1.0,
                    'sharpe_ratio': br.sharpe_ratio,
                    'win_rate': br.win_rate,
                    'total_trades': br.trades,
                    'pf': br.profit_factor,
                    'grade': br.stability
                }
                results.append(result_dict)

            logger.info(f"최적화 완료: {len(results)}개 결과")
            self.finished.emit(results)

        except Exception as e:
            import traceback
            error_msg = f"최적화 실행 중 에러: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error.emit(error_msg)

        finally:
            # CRITICAL #1: 워커 종료 시 리소스 정리 (v7.27)
            self._cleanup_resources()
            logger.info("[OptimizationWorker] 리소스 정리 완료")

    def cancel(self):
        """최적화 취소"""
        logger.info("최적화 취소 요청")
        self._cancelled = True

        if self.engine and hasattr(self.engine, 'cancel'):
            self.engine.cancel()

        # 스레드 강제 종료 (마지막 수단)
        if self.isRunning():
            self.quit()
            self.wait(2000)  # 2초 대기

            if self.isRunning():
                logger.warning("강제 종료 시도")
                self.terminate()

    def _cleanup_resources(self):
        """
        CRITICAL #1: 워커 종료 시 리소스 정리 (v7.27)

        취소, 오류, 정상 완료 모두 여기서 정리됩니다.
        """
        try:
            # 1. DataFrame 참조 해제
            if hasattr(self, 'df') and self.df is not None:
                del self.df
                self.df = None

            # 2. 파라미터 그리드 정리 (대용량 조합 시 메모리 누수 방지)
            if hasattr(self, 'param_grid'):
                self.param_grid = []

            # 3. Optimizer 엔진 정리
            if hasattr(self, 'engine') and self.engine is not None:
                self.engine = None

        except Exception as e:
            logger.warning(f"[OptimizationWorker] 리소스 정리 중 경고: {e}")


__all__ = ['OptimizationWorker']
