"""
트레이딩 시그널 모듈
==================

시그널 생성 및 관리

Classes:
    TradeSignal: 거래 시그널 데이터 클래스
    SignalGenerator: 시그널 생성기
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """
    거래 시그널 데이터 클래스
    
    Attributes:
        signal_type: 시그널 타입 ('Long', 'Short')
        pattern: 패턴 타입 ('W', 'M')
        stop_loss: 스탑로스 가격
        atr: ATR 값
        timestamp: 시그널 발생 시각
        entry_price: 진입 가격 (옵션)
        take_profit: 익절 가격 (옵션)
        confidence: 신뢰도 (0~1)
        metadata: 추가 메타데이터
    """
    signal_type: str  # 'Long', 'Short'
    pattern: str  # 'W', 'M'
    stop_loss: float
    atr: float
    timestamp: datetime
    entry_price: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.5
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def is_long(self) -> bool:
        """롱 시그널 여부"""
        return self.signal_type == 'Long'
    
    def is_short(self) -> bool:
        """숏 시그널 여부"""
        return self.signal_type == 'Short'
    
    def risk_reward_ratio(self) -> Optional[float]:
        """리스크-리워드 비율 계산"""
        if not self.entry_price or not self.take_profit:
            return None
        
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        
        if risk == 0:
            return None
        
        return reward / risk
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'signal_type': self.signal_type,
            'pattern': self.pattern,
            'stop_loss': self.stop_loss,
            'atr': self.atr,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'entry_price': self.entry_price,
            'take_profit': self.take_profit,
            'confidence': self.confidence,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeSignal':
        """딕셔너리에서 생성"""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            signal_type=data['signal_type'],
            pattern=data['pattern'],
            stop_loss=data['stop_loss'],
            atr=data['atr'],
            timestamp=timestamp,
            entry_price=data.get('entry_price'),
            take_profit=data.get('take_profit'),
            confidence=data.get('confidence', 0.5),
            metadata=data.get('metadata'),
        )


class SignalGenerator:
    """
    시그널 생성기
    
    지표를 기반으로 매수/매도 시그널 생성
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Args:
            params: 전략 파라미터
        """
        self.params = params or {}
        self.signals: List[TradeSignal] = []
        
    def generate_signal(self, indicators: Dict[str, Any], 
                        current_price: float,
                        timestamp: Optional[datetime] = None) -> Optional[TradeSignal]:
        """
        지표를 기반으로 시그널 생성
        
        Args:
            indicators: 지표 딕셔너리 (rsi, macd, ema, atr 등)
            current_price: 현재 가격
            timestamp: 시각 (기본값: 현재)
        
        Returns:
            TradeSignal 또는 None
        """
        timestamp = timestamp or datetime.now()
        
        rsi = indicators.get('rsi')
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')
        ema = indicators.get('ema')
        atr = indicators.get('atr', 0)
        
        signal = None
        
        # 롱 조건
        if self._check_long_conditions(indicators, current_price):
            stop_loss = current_price - (atr * self.params.get('atr_mult', 2.0))
            signal = TradeSignal(
                signal_type='Long',
                pattern='W',
                stop_loss=stop_loss,
                atr=atr,
                timestamp=timestamp,
                entry_price=current_price,
                confidence=self._calculate_confidence(indicators, 'Long'),
            )
        
        # 숏 조건
        elif self._check_short_conditions(indicators, current_price):
            stop_loss = current_price + (atr * self.params.get('atr_mult', 2.0))
            signal = TradeSignal(
                signal_type='Short',
                pattern='M',
                stop_loss=stop_loss,
                atr=atr,
                timestamp=timestamp,
                entry_price=current_price,
                confidence=self._calculate_confidence(indicators, 'Short'),
            )
        
        if signal:
            self.signals.append(signal)
            logger.debug(f"Signal generated: {signal.signal_type} at {current_price}")
        
        return signal
    
    def _check_long_conditions(self, indicators: Dict[str, Any], 
                                price: float) -> bool:
        """롱 진입 조건 확인"""
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        ema = indicators.get('ema', price)
        
        # 기본 조건
        rsi_oversold = rsi < self.params.get('pullback_rsi_long', 35)
        macd_bullish = macd > macd_signal
        price_above_ema = price > ema
        
        return rsi_oversold and macd_bullish and price_above_ema
    
    def _check_short_conditions(self, indicators: Dict[str, Any],
                                 price: float) -> bool:
        """숏 진입 조건 확인"""
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        ema = indicators.get('ema', price)
        
        # 기본 조건
        rsi_overbought = rsi > self.params.get('pullback_rsi_short', 65)
        macd_bearish = macd < macd_signal
        price_below_ema = price < ema
        
        return rsi_overbought and macd_bearish and price_below_ema
    
    def _calculate_confidence(self, indicators: Dict[str, Any],
                               signal_type: str) -> float:
        """시그널 신뢰도 계산"""
        confidence = 0.5
        
        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        
        # RSI 극단값일수록 높은 신뢰도
        if signal_type == 'Long' and rsi < 30:
            confidence += 0.2
        elif signal_type == 'Short' and rsi > 70:
            confidence += 0.2
        
        # MACD 강도
        macd_diff = abs(macd - macd_signal)
        if macd_diff > 0.001:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_recent_signals(self, count: int = 10) -> List[TradeSignal]:
        """최근 시그널 조회"""
        return self.signals[-count:]
    
    def clear_signals(self) -> None:
        """시그널 초기화"""
        self.signals = []
