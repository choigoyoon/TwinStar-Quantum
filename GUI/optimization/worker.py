# GUI/optimization/worker.py
"""최적화 워커 스레드"""

from .common import *


class OptimizationWorker(QThread):
    """Optimization execution thread"""
    
    progress = pyqtSignal(int, int)  # completed, total
    task_done = pyqtSignal(object)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, engine, df, param_grid, max_workers=4, 
                 symbol="", timeframe="", capital_mode="compound"):
        super().__init__()
        self.engine = engine
        self.df = df
        self.param_grid = param_grid
        self.max_workers = max_workers
        self.symbol = symbol
        self.timeframe = timeframe
        self.capital_mode = capital_mode
    
    def run(self):
        try:
            self.engine.progress_callback = self.progress.emit
            
            results = self.engine.run_optimization(
                self.df,
                self.param_grid, 
                max_workers=self.max_workers,
                task_callback=self.task_done.emit,
                capital_mode=self.capital_mode
            )
            self.finished.emit(results)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def cancel(self):
        if self.engine:
            self.engine.cancel()
