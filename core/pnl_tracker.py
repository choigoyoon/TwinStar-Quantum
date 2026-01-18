import logging
import time
from datetime import datetime

class PnLTracker:
    """거래소 API와 로컬 계산 PnL 동기화 및 정확도 관리"""
    
    def __init__(self, exchange_adapter, sync_threshold: float = 0.5):
        self.exchange = exchange_adapter
        self.local_pnl = 0.0
        self.api_pnl = 0.0
        self.last_sync = datetime.now()
        self.sync_threshold = sync_threshold # 동기화 경고 임계값 (USD)
        self.logger = logging.getLogger("PnLTracker")
        self._cached_api_pnl = 0.0
        self._cache_time = 0

    def add_local_pnl(self, pnl: float) -> None:
        """로컬 매매 종료 시 손익 추가"""
        self.local_pnl += pnl
        self.logger.info(f"📝 로컬 PnL 업데이트: ${pnl:+.2f} (누적: ${self.local_pnl:.2f})")

    def sync_with_exchange(self) -> float:
        """거래소 API에서 실제 실현 손익을 가져와 차이 확인"""
        current_time = time.time()
        # API 호출 최소화 (60초 캐싱)
        if current_time - self._cache_time < 60:
            return self.api_pnl - self.local_pnl

        try:
            if hasattr(self.exchange, 'get_realized_pnl'):
                # API 호출
                self.api_pnl = self.exchange.get_realized_pnl()
                self._cached_api_pnl = self.api_pnl
                self._cache_time = current_time
                self.last_sync = datetime.now()
                
                diff = self.api_pnl - self.local_pnl
                if abs(diff) > self.sync_threshold:
                    self.logger.warning(
                        f"⚖️ PnL 오차 발견: API(${self.api_pnl:.2f}) vs Local(${self.local_pnl:.2f}) "
                        f"| 차이: ${diff:+.2f}"
                    )
                return diff
        except Exception as e:
            self.logger.error(f"❌ API PnL 동기화 실패 (로컬 데이터 유지): {e}")
            
        return 0.0

    def get_accurate_pnl(self) -> float:
        """가장 최근의 정확한 PnL 반환 (API 우선, 실패 시 로컬)"""
        if time.time() - self._cache_time > 300: # 5분 이상 경과 시 강제 동기화 시도
            self.sync_with_exchange()
            
        if self._cache_time > 0:
            return self.api_pnl
        return self.local_pnl
