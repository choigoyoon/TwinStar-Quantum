# live_trading_manager.py - 실매매 관리자 스텁 모듈

from dataclasses import dataclass
from typing import Optional, Callable, List


@dataclass
class TradingConfig:
    """거래 설정"""
    strategy_id: str = ""
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    leverage: int = 1
    position_size: float = 0.01
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 2.0


class LiveTradingManager:
    """실매매 관리자 (스텁)"""
    
    def __init__(self):
        self.is_running = False
        self.config: Optional[TradingConfig] = None
        
        # 콜백
        self.on_signal: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_status_change: Optional[Callable] = None
    
    def start(self, api_key: str, api_secret: str, config: TradingConfig, testnet: bool = False) -> bool:
        """거래 시작"""
        self.config = config
        self.is_running = True
        if self.on_status_change:
            self.on_status_change("Started")
        return True
    
    def stop(self):
        """거래 중지"""
        self.is_running = False
        if self.on_status_change:
            self.on_status_change("Stopped")
    
    def get_positions(self) -> List:
        """현재 포지션 조회"""
        return []
    
    def get_current_prices(self) -> dict:
        """현재 가격 조회"""
        return {}
