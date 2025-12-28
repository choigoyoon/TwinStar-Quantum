# strategies/example_strategy.py
# 새 전략 만들기 템플릿 - 이 파일을 복사해서 수정하세요!

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from .common.strategy_interface import (
    BaseStrategy, StrategyConfig, TradeSignal, Candle,
    SignalType, TradeStatus
)


@dataclass
class ExampleParams:
    """전략 파라미터 - 최적화할 값들"""
    ema_fast: int = 10
    ema_slow: int = 20
    rsi_period: int = 14
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    atr_period: int = 14
    risk_reward: float = 2.0
    
    def to_dict(self) -> dict:
        return {
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold,
            'atr_period': self.atr_period,
            'risk_reward': self.risk_reward
        }


class ExampleStrategy(BaseStrategy):
    """
    예시 전략 템플릿
    
    이 파일을 복사하고 아래 항목을 수정하세요:
    1. _init_config(): 전략 ID, 이름, 설명 변경
    2. check_signal(): 진입 로직 구현
    """
    
    def __init__(self, params: ExampleParams = None):
        self.params = params or ExampleParams()
        super().__init__()
    
    def _init_config(self) -> StrategyConfig:
        """전략 설정 - 수정 필요!"""
        return StrategyConfig(
            strategy_id="example_v1",          # ← 고유 ID로 변경
            name="Example Strategy",           # ← 전략 이름
            version="1.0.0",
            description="EMA 크로스오버 + RSI 필터 예시",
            timeframe="1h",                    # ← 사용 타임프레임
            symbols=["BTCUSDT", "ETHUSDT"],
            tier_required="basic"
        )
    
    def _calculate_ema(self, close: pd.Series, period: int) -> pd.Series:
        """EMA 계산"""
        return close.ewm(span=period, adjust=False).mean()
    
    def _calculate_rsi(self, close: pd.Series, period: int) -> float:
        """RSI 계산"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> float:
        """ATR 계산"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean().iloc[-1]
    
    def check_signal(self, candles: List[Candle]) -> Optional[TradeSignal]:
        """
        신호 체크 - 핵심 로직!
        
        이 함수를 수정해서 원하는 진입 조건을 구현하세요.
        """
        if len(candles) < max(self.params.ema_slow, self.params.rsi_period) + 10:
            return None
        
        # DataFrame 변환
        df = pd.DataFrame([{
            'timestamp': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles])
        
        close = df['close']
        
        # 지표 계산
        ema_fast = self._calculate_ema(close, self.params.ema_fast)
        ema_slow = self._calculate_ema(close, self.params.ema_slow)
        rsi = self._calculate_rsi(close, self.params.rsi_period)
        atr = self._calculate_atr(df, self.params.atr_period)
        
        current_price = close.iloc[-1]
        current_idx = len(df) - 1
        
        # ========== 롱 조건 ==========
        # EMA 골든크로스 + RSI 과매도 탈출
        if (ema_fast.iloc[-1] > ema_slow.iloc[-1] and 
            ema_fast.iloc[-2] <= ema_slow.iloc[-2] and
            rsi < 50):
            
            sl = current_price - (atr * 2)
            tp = current_price + (atr * 2 * self.params.risk_reward)
            
            return TradeSignal(
                signal_type=SignalType.LONG,
                symbol=self.config.symbols[0],
                timeframe=self.config.timeframe,
                entry_price=current_price,
                stop_loss=sl,
                take_profit=tp,
                candle_index=current_idx,
                trade_id=f"EX_L_{current_idx}_{int(datetime.now().timestamp())}"
            )
        
        # ========== 숏 조건 ==========
        # EMA 데드크로스 + RSI 과매수 탈출
        if (ema_fast.iloc[-1] < ema_slow.iloc[-1] and 
            ema_fast.iloc[-2] >= ema_slow.iloc[-2] and
            rsi > 50):
            
            sl = current_price + (atr * 2)
            tp = current_price - (atr * 2 * self.params.risk_reward)
            
            return TradeSignal(
                signal_type=SignalType.SHORT,
                symbol=self.config.symbols[0],
                timeframe=self.config.timeframe,
                entry_price=current_price,
                stop_loss=sl,
                take_profit=tp,
                candle_index=current_idx,
                trade_id=f"EX_S_{current_idx}_{int(datetime.now().timestamp())}"
            )
        
        return None
    
    def update_params(self, **kwargs):
        """파라미터 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self.params, key):
                setattr(self.params, key, value)


# 이 파일을 strategies/ 폴더에 저장하면 자동으로 인식됩니다!
