# trade_executor.py - 거래 실행기 스텁 모듈

from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import Enum

# Logging
import logging
logger = logging.getLogger(__name__)


class PositionSide(Enum):
    NONE = "none"
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    side: PositionSide = PositionSide.NONE
    size: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    leverage: int = 1
    stop_loss: float = 0.0
    take_profit: float = 0.0
    entry_time: Optional[datetime] = None
    
    @property
    def pnl_percent(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == PositionSide.LONG:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        elif self.side == PositionSide.SHORT:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100
        return 0.0


class TradeExecutor:
    """거래 실행기 (스텁)"""
    
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.positions = {}
    
    def place_market_order(self, symbol: str, side: str, qty: float, 
                           stop_loss: float = None, take_profit: float = None):
        """시장가 주문"""
        logger.info(f"[TradeExecutor] 시장가 주문: {symbol} {side} {qty}")
        return {"orderId": "stub_order_001", "status": "ok"}
    
    def close_position(self, symbol: str):
        """포지션 청산"""
        logger.info(f"[TradeExecutor] 포지션 청산: {symbol}")
        return {"status": "ok"}
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """포지션 조회"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> list:
        """모든 포지션 조회"""
        return list(self.positions.values())
