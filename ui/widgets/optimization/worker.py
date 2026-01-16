"""
ui/widgets/optimization/worker.py

최적화 백그라운드 워커 (QThread)

Zone A 마이그레이션:
    - GUI/optimization_widget.py에서 OptimizationWorker 추출
    - 타입 안전성 확보
    - 취소 기능 개선

타입 안전성 강화 (v7.12 - 2026-01-16)
"""

import logging
from typing import Optional, Any
from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd

logger = logging.getLogger(__name__)


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
        param_grid: dict,
        max_workers: int = 4,
        symbol: str = "",
        timeframe: str = "",
        capital_mode: str = "compound",
        parent: Optional[QThread] = None
    ):
        """
        Args:
            engine: OptimizationEngine 인스턴스
            df: 백테스트 데이터프레임
            param_grid: 파라미터 그리드 {'atr_mult': [1.5, 2.0], ...}
            max_workers: 최대 워커 수 (기본: 4)
            symbol: 심볼 (로깅용)
            timeframe: 타임프레임 (로깅용)
            capital_mode: 자본 모드 ('compound' or 'fixed')
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
        self._cancelled = False

        logger.debug(
            f"OptimizationWorker 초기화: {symbol} {timeframe}, "
            f"max_workers={max_workers}, capital_mode={capital_mode}"
        )
    
    def run(self):
        """최적화 실행 (백그라운드 스레드)"""
        try:
            logger.info(f"최적화 시작: {self.symbol} {self.timeframe}")

            # 진행률 콜백 설정
            self.engine.progress_callback = self.progress.emit

            # 최적화 실행
            results = self.engine.run_optimization(
                self.df,
                self.param_grid,
                max_workers=self.max_workers,
                task_callback=self.task_done.emit,
                capital_mode=self.capital_mode
            )

            if self._cancelled:
                logger.info("최적화 취소됨")
                self.error.emit("사용자가 최적화를 취소했습니다.")
                return

            logger.info(f"최적화 완료: {len(results)}개 결과")
            self.finished.emit(results)

        except Exception as e:
            import traceback
            error_msg = f"최적화 실행 중 에러: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.error.emit(error_msg)

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


__all__ = ['OptimizationWorker']
