from PyQt6.QtCore import QObject, pyqtSignal

# Logging
import logging
logger = logging.getLogger(__name__)

class ExternalDataWorker(QObject):
    """외부 포지션 조회 백그라운드 워커"""
    finished = pyqtSignal(list)
    
    def __init__(self, exchange_manager):
        super().__init__()
        self.exchange_manager = exchange_manager
    
    def run(self):
        """백그라운드에서 외부 포지션 조회"""
        positions = []
        try:
            if self.exchange_manager:
                # [FIX] em.configs.keys()를 사용하여 설정된 모든 거래소 시도
                for name in self.exchange_manager.configs.keys():
                    try:
                        pos_list = self.exchange_manager.get_positions(name)
                        if pos_list:
                            for p in pos_list:
                                p['exchange'] = name
                                positions.append(p)
                    except Exception as e:
                        logger.info(f"[ExternalDataWorker] {name} 포지션 조회 실패: {e}")
        except Exception as e:
            logger.info(f"[ExternalDataWorker] 전체 오류: {e}")
        
        self.finished.emit(positions)
