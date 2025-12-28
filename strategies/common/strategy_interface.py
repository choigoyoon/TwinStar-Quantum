# strategies/common/strategy_interface.py
# 전략 인터페이스 정의

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
import pandas as pd


# ============================================================
# 신호 타입 정의
# ============================================================

class SignalType(Enum):
    NONE = "none"
    LONG = "long"
    SHORT = "short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class TradeStatus(Enum):
    PENDING = "pending"
    ENTRY = "entry"
    TP_HIT = "tp_hit"
    SL_HIT = "sl_hit"
    CLOSED = "closed"


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class Candle:
    """캔들 데이터"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class TradeSignal:
    """거래 신호"""
    signal_type: SignalType
    symbol: str
    timeframe: str
    
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    signal_time: datetime = field(default_factory=datetime.now)
    candle_index: int = -1
    
    trade_id: str = ""
    
    status: TradeStatus = TradeStatus.PENDING
    exit_price: float = 0.0
    exit_time: Optional[datetime] = None
    pnl_percent: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'signal_type': self.signal_type.value,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'signal_time': self.signal_time.isoformat() if self.signal_time else None,
            'trade_id': self.trade_id,
            'status': self.status.value,
            'pnl_percent': self.pnl_percent
        }


@dataclass
class StrategyConfig:
    """전략 설정"""
    strategy_id: str
    name: str
    version: str
    description: str
    
    timeframe: str
    symbols: List[str]
    
    win_rate: float = 0.0
    avg_profit: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    
    tier_required: str = "basic"


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_id: str
    symbol: str
    timeframe: str
    
    start_date: datetime
    end_date: datetime
    
    trades: List[TradeSignal] = field(default_factory=list)
    candles: List[Candle] = field(default_factory=list)
    
    total_trades: int = 0
    win_count: int = 0
    lose_count: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    
    ohlcv: Optional[pd.DataFrame] = None
    equity_curve: List[float] = field(default_factory=list)


# ============================================================
# 베이스 전략 클래스
# ============================================================

class BaseStrategy(ABC):
    """모든 전략이 상속받는 베이스 클래스"""
    
    def __init__(self):
        self.config: StrategyConfig = self._init_config()
        self.last_signal_index: int = -100
        self.min_bars_between: int = 10
    
    @abstractmethod
    def _init_config(self) -> StrategyConfig:
        """전략 설정 초기화"""
        pass
    
    @abstractmethod
    def check_signal(self, candles: List[Candle]) -> Optional[TradeSignal]:
        """신호 체크"""
        pass
    
    def get_config(self) -> StrategyConfig:
        """설정 반환"""
        return self.config
    
    def can_trade(self, current_index: int) -> bool:
        """최소 간격 체크"""
        return (current_index - self.last_signal_index) >= self.min_bars_between
