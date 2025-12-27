# capital_manager.py - 자금 관리자 스텁 모듈

from dataclasses import dataclass
from typing import Optional


@dataclass
class CapitalConfig:
    """자금 관리 설정"""
    initial_capital: float = 10000.0
    risk_per_trade: float = 2.0  # 거래당 리스크 %
    max_position_size: float = 10.0  # 최대 포지션 크기 %
    max_leverage: int = 10
    use_compounding: bool = True
    drawdown_limit: float = 20.0  # 최대 손실 한도 %


@dataclass
class PositionSizing:
    """포지션 사이징 결과"""
    position_size: float = 0.0
    position_value: float = 0.0
    risk_amount: float = 0.0
    leverage: int = 1
    liquidation_price: float = 0.0
    warning: str = ""


class CapitalManager:
    """자금 관리자 (스텁)"""
    
    def __init__(self, config: CapitalConfig = None):
        self.config = config or CapitalConfig()
        self.current_capital = self.config.initial_capital
        self.peak_capital = self.config.initial_capital
        self.total_pnl = 0.0
        self.trade_count = 0
    
    def update_config(self, config: CapitalConfig):
        """설정 업데이트"""
        self.config = config
    
    def calculate_position(self, entry_price: float, stop_loss: float, 
                          leverage: int = 1) -> PositionSizing:
        """포지션 사이징 계산"""
        result = PositionSizing()
        
        if entry_price <= 0 or stop_loss <= 0:
            result.warning = "Invalid prices"
            return result
        
        # 리스크 금액
        risk_amount = self.current_capital * (self.config.risk_per_trade / 100)
        result.risk_amount = risk_amount
        
        # 손절폭
        sl_distance = abs(entry_price - stop_loss)
        sl_percent = (sl_distance / entry_price) * 100
        
        if sl_percent == 0:
            result.warning = "Stop loss too close"
            return result
        
        # 포지션 가치 = 리스크 금액 / 손절폭
        position_value = risk_amount / (sl_percent / 100)
        
        # 최대 포지션 제한
        max_position_value = self.current_capital * (self.config.max_position_size / 100) * leverage
        if position_value > max_position_value:
            position_value = max_position_value
            result.warning = "Position capped at max size"
        
        result.position_value = position_value
        result.position_size = position_value / entry_price
        result.leverage = min(leverage, self.config.max_leverage)
        
        # 청산가 계산 (롱 기준)
        result.liquidation_price = entry_price * (1 - 1 / result.leverage)
        
        return result
    
    def update_capital(self, pnl: float):
        """자본 업데이트"""
        self.current_capital += pnl
        self.total_pnl += pnl
        self.trade_count += 1
        
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
    
    def get_drawdown(self) -> float:
        """현재 드로우다운 계산"""
        if self.peak_capital == 0:
            return 0.0
        return ((self.peak_capital - self.current_capital) / self.peak_capital) * 100
    
    def can_trade(self) -> bool:
        """거래 가능 여부"""
        return self.get_drawdown() < self.config.drawdown_limit
    
    def get_status(self) -> dict:
        """현재 상태"""
        return {
            "current_capital": self.current_capital,
            "initial_capital": self.config.initial_capital,
            "total_pnl": self.total_pnl,
            "total_pnl_percent": (self.total_pnl / self.config.initial_capital) * 100,
            "peak_capital": self.peak_capital,
            "drawdown": self.get_drawdown(),
            "trade_count": self.trade_count,
            "can_trade": self.can_trade()
        }
