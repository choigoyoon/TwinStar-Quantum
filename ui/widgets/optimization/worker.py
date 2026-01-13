"""
TwinStar Quantum - Optimization Worker
======================================

백그라운드 최적화 실행 워커
"""

import logging
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class OptimizationWorker(QThread):
    """
    최적화 실행 백그라운드 워커
    
    Signals:
        progress(int, int): (완료 수, 전체 수)
        task_done(object): 개별 태스크 완료
        finished(list): 전체 완료, 결과 리스트
        error(str): 에러 발생
    """
    
    progress = pyqtSignal(int, int)
    task_done = pyqtSignal(object)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(
        self, 
        engine, 
        df, 
        param_grid, 
        max_workers: int = 4, 
        symbol: str = "", 
        timeframe: str = "",
        capital_mode: str = "compound"
    ):
        super().__init__()
        self.engine = engine
        self.df = df
        self.param_grid = param_grid
        self.max_workers = max_workers
        self.symbol = symbol
        self.timeframe = timeframe
        self.capital_mode = capital_mode
        self._cancelled = False
    
    def run(self):
        """최적화 실행"""
        try:
            # 진행률 콜백 설정
            self.engine.progress_callback = self.progress.emit
            
            results = self.engine.run_optimization(
                self.df,
                self.param_grid,
                max_workers=self.max_workers,
                task_callback=self.task_done.emit,
                capital_mode=self.capital_mode
            )
            
            if not self._cancelled:
                self.finished.emit(results)
                
        except Exception as e:
            import traceback
            logger.error(f"최적화 실행 오류: {e}")
            traceback.print_exc()
            self.error.emit(str(e))
    
    def cancel(self):
        """최적화 취소"""
        self._cancelled = True
        if self.engine:
            self.engine.cancel()
        logger.info("🛑 최적화 취소됨")
