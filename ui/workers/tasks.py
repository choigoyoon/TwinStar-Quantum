"""
Background Workers
==================

백테스트/최적화 실행을 위한 QThread 워커
trading/ 패키지와 직접 연동
"""

from PyQt5.QtCore import QThread, pyqtSignal
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BacktestWorker(QThread):
    """
    백테스트 실행 워커
    
    Signals:
        progress(int): 진행률 (0-100)
        finished(dict): 완료 시 결과 딕셔너리
        error(str): 에러 발생 시 메시지
    """
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, df: pd.DataFrame, strategy: str, timeframe: str, 
                 params: dict = None, apply_filters: bool = True):
        super().__init__()
        self.df = df
        self.strategy = strategy
        self.timeframe = timeframe
        self.params = params
        self.apply_filters = apply_filters
        self._cancelled = False
    
    def run(self):
        try:
            self.progress.emit(10)
            
            # trading 패키지 임포트
            from trading import run_backtest, get_strategy, SANDBOX_PARAMS
            from trading.core import calculate_grade
            
            self.progress.emit(30)
            
            # 파라미터 설정
            params = self.params or SANDBOX_PARAMS.copy()
            
            # 전략 생성 및 백테스트 실행
            strategy_obj = get_strategy(self.strategy, params)
            
            self.progress.emit(50)
            
            if self._cancelled:
                return
            
            # 백테스트 실행
            result = strategy_obj.backtest(
                self.df, 
                timeframe=self.timeframe,
                apply_filters=self.apply_filters
            )
            
            self.progress.emit(80)
            
            if self._cancelled:
                return
            
            # 등급 계산
            grade = calculate_grade(
                result.get('win_rate', 0),
                result.get('profit_factor', 0),
                result.get('max_drawdown', 100)
            )
            result['grade'] = grade
            result['strategy'] = self.strategy
            result['params'] = params
            
            self.progress.emit(100)
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def cancel(self):
        """작업 취소"""
        self._cancelled = True


class OptimizationWorker(QThread):
    """
    최적화 실행 워커
    
    Signals:
        progress(int, int): (완료된 작업 수, 전체 작업 수)
        task_done(dict): 개별 작업 완료 시 결과
        finished(list): 모든 작업 완료 시 결과 리스트
        error(str): 에러 발생 시 메시지
    """
    
    progress = pyqtSignal(int, int)
    task_done = pyqtSignal(dict)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, df: pd.DataFrame, strategy: str, timeframe: str,
                 mode: str = 'quick', apply_filters: bool = True):
        super().__init__()
        self.df = df
        self.strategy = strategy
        self.timeframe = timeframe
        self.mode = mode
        self.apply_filters = apply_filters
        self._cancelled = False
    
    def run(self):
        try:
            from trading import get_strategy, SANDBOX_PARAMS
            from trading.core import calculate_grade
            from trading.backtest import Optimizer
            
            # 전략 객체 생성
            strategy_obj = get_strategy(self.strategy)
            
            # 최적화 실행
            optimizer = Optimizer()
            
            # 그리드 생성
            if self.mode == 'quick':
                param_grid = {
                    'atr_mult': [1.5, 2.0, 2.5],
                    'trail_start': [1.0, 1.2, 1.5],
                    'trail_dist': [0.02, 0.03, 0.05],
                }
            elif self.mode == 'standard':
                param_grid = {
                    'atr_mult': [1.25, 1.5, 1.75, 2.0, 2.25, 2.5],
                    'trail_start': [0.8, 1.0, 1.2, 1.5, 2.0],
                    'trail_dist': [0.02, 0.03, 0.05, 0.08],
                    'tolerance': [0.08, 0.10, 0.12],
                }
            else:  # deep
                param_grid = {
                    'atr_mult': [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0],
                    'trail_start': [0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5],
                    'trail_dist': [0.02, 0.03, 0.05, 0.08, 0.10],
                    'tolerance': [0.06, 0.08, 0.10, 0.12, 0.14],
                    'adx_min': [5, 10, 15, 20],
                }
            
            # 그리드 조합 생성
            import itertools
            keys = list(param_grid.keys())
            combinations = list(itertools.product(*param_grid.values()))
            total = len(combinations)
            
            results = []
            base_params = SANDBOX_PARAMS.copy()
            
            for i, values in enumerate(combinations):
                if self._cancelled:
                    break
                
                # 파라미터 설정
                params = base_params.copy()
                for j, key in enumerate(keys):
                    params[key] = values[j]
                
                # 백테스트 실행
                try:
                    strategy_obj = get_strategy(self.strategy, params)
                    result = strategy_obj.backtest(
                        self.df,
                        timeframe=self.timeframe,
                        apply_filters=self.apply_filters
                    )
                    
                    # 등급 계산
                    grade = calculate_grade(
                        result.get('win_rate', 0),
                        result.get('profit_factor', 0),
                        result.get('max_drawdown', 100)
                    )
                    result['grade'] = grade
                    result['params'] = params.copy()
                    
                    results.append(result)
                    self.task_done.emit(result)
                    
                except Exception as e:
                    logger.warning(f"Optimization task failed: {e}")
                
                self.progress.emit(i + 1, total)
            
            # 결과 정렬 (PnL 기준)
            results.sort(key=lambda x: x.get('simple_pnl', 0), reverse=True)
            
            self.finished.emit(results)
            
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def cancel(self):
        """작업 취소"""
        self._cancelled = True
