"""
TwinStar Quantum - Backtest Worker
==================================

백그라운드 백테스트 실행 워커
"""

import logging
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class BacktestWorker(QThread):
    """
    백테스트 실행 백그라운드 워커
    
    Signals:
        progress(int): 진행률 (0-100)
        finished(list, object, object): 완료 (trades, df, params)
        error(str): 에러 발생
    """
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(list, object, object)
    error = pyqtSignal(str)
    
    def __init__(
        self,
        engine,
        df,
        params: dict,
        exchange: str = "",
        symbol: str = "",
        timeframe: str = ""
    ):
        super().__init__()
        self.engine = engine
        self.df = df
        self.params = params
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self._cancelled = False
    
    def run(self):
        """백테스트 실행"""
        try:
            logger.info(f"🚀 백테스트 시작: {self.symbol} ({self.timeframe})")
            
            # 진행률 콜백 설정
            if hasattr(self.engine, 'progress_callback'):
                self.engine.progress_callback = self._on_progress
            
            # 백테스트 실행
            trades = self.engine.run(
                self.df,
                self.params
            )
            
            if not self._cancelled:
                self.finished.emit(trades, self.df, self.params)
                logger.info(f"✅ 백테스트 완료: {len(trades)}건 거래")
                
        except Exception as e:
            import traceback
            logger.error(f"❌ 백테스트 오류: {e}")
            traceback.print_exc()
            self.error.emit(str(e))
    
    def _on_progress(self, value: int):
        """진행률 업데이트"""
        self.progress.emit(value)
    
    def cancel(self):
        """백테스트 취소"""
        self._cancelled = True
        if hasattr(self.engine, 'cancel'):
            self.engine.cancel()
        logger.info("🛑 백테스트 취소됨")
