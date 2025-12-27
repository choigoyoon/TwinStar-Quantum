# candle_aggregator.py - 캔들 집계기 모듈

from dataclasses import dataclass
from typing import Dict, Optional, Callable, List
from datetime import datetime
from enum import Enum


@dataclass
class Candle:
    """캔들 데이터"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    is_closed: bool = False


class CandleAggregator:
    """실시간 캔들 집계기
    
    1분봉 데이터를 받아서 상위 타임프레임 캔들로 집계
    """
    
    # 타임프레임별 분 단위
    TF_MINUTES = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
        '1d': 1440, '3d': 4320, '1w': 10080
    }
    
    def __init__(self, target_timeframes: List[str] = None):
        """
        Args:
            target_timeframes: 집계할 타임프레임 리스트 (예: ['5m', '15m', '1h'])
        """
        self.target_timeframes = target_timeframes or ['5m', '15m', '1h', '4h', '1d']
        
        # 타임프레임별 현재 집계 중인 캔들
        self.current_candles: Dict[str, Candle] = {}
        
        # 콜백
        self.on_candle_update: Optional[Callable[[str, Candle, bool], None]] = None
        self.on_candle_closed: Optional[Callable[[str, Candle], None]] = None
    
    def _get_candle_open_time(self, timestamp_ms: int, timeframe: str) -> int:
        """캔들 시작 시간 계산"""
        minutes = self.TF_MINUTES.get(timeframe, 1)
        period_ms = minutes * 60 * 1000
        return (timestamp_ms // period_ms) * period_ms
    
    def process_tick(self, timestamp_ms: int, price: float, volume: float = 0.0):
        """틱 데이터 처리 (가격 업데이트)"""
        for tf in self.target_timeframes:
            self._update_candle(tf, timestamp_ms, price, volume)
    
    def process_candle(self, candle: Candle, base_timeframe: str = '1m'):
        """1분봉 캔들 데이터 처리"""
        for tf in self.target_timeframes:
            if tf == base_timeframe:
                # 같은 타임프레임이면 그대로 전달
                if self.on_candle_update:
                    self.on_candle_update(tf, candle, candle.is_closed)
                if candle.is_closed and self.on_candle_closed:
                    self.on_candle_closed(tf, candle)
            else:
                # 상위 타임프레임으로 집계
                self._aggregate_candle(tf, candle)
    
    def _update_candle(self, timeframe: str, timestamp_ms: int, price: float, volume: float):
        """캔들 업데이트"""
        open_time = self._get_candle_open_time(timestamp_ms, timeframe)
        
        current = self.current_candles.get(timeframe)
        
        if current is None or current.timestamp != open_time:
            # 새 캔들 시작
            if current and current.timestamp != open_time:
                # 이전 캔들 완성
                current.is_closed = True
                if self.on_candle_closed:
                    self.on_candle_closed(timeframe, current)
            
            # 새 캔들 생성
            self.current_candles[timeframe] = Candle(
                timestamp=open_time,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                is_closed=False
            )
        else:
            # 기존 캔들 업데이트
            current.high = max(current.high, price)
            current.low = min(current.low, price)
            current.close = price
            current.volume += volume
        
        if self.on_candle_update:
            self.on_candle_update(timeframe, self.current_candles[timeframe], False)
    
    def _aggregate_candle(self, timeframe: str, source_candle: Candle):
        """소스 캔들을 상위 타임프레임으로 집계"""
        open_time = self._get_candle_open_time(source_candle.timestamp, timeframe)
        
        current = self.current_candles.get(timeframe)
        
        if current is None or current.timestamp != open_time:
            # 새 캔들 시작
            if current and current.timestamp != open_time:
                # 이전 캔들 완성
                current.is_closed = True
                if self.on_candle_closed:
                    self.on_candle_closed(timeframe, current)
            
            # 새 캔들 생성
            self.current_candles[timeframe] = Candle(
                timestamp=open_time,
                open=source_candle.open,
                high=source_candle.high,
                low=source_candle.low,
                close=source_candle.close,
                volume=source_candle.volume,
                is_closed=False
            )
        else:
            # 기존 캔들 업데이트
            current.high = max(current.high, source_candle.high)
            current.low = min(current.low, source_candle.low)
            current.close = source_candle.close
            current.volume += source_candle.volume
        
        if self.on_candle_update:
            self.on_candle_update(timeframe, self.current_candles[timeframe], False)
    
    def get_current_candle(self, timeframe: str) -> Optional[Candle]:
        """현재 집계 중인 캔들 반환"""
        return self.current_candles.get(timeframe)
    
    def reset(self):
        """상태 초기화"""
        self.current_candles.clear()


# 테스트
if __name__ == "__main__":
    aggregator = CandleAggregator(['5m', '15m', '1h'])
    
    def on_update(tf, candle, is_closed):
        print(f"[{tf}] Update: O={candle.open:.2f} H={candle.high:.2f} L={candle.low:.2f} C={candle.close:.2f}")
    
    def on_closed(tf, candle):
        print(f"[{tf}] ✅ CLOSED: O={candle.open:.2f} H={candle.high:.2f} L={candle.low:.2f} C={candle.close:.2f}")
    
    aggregator.on_candle_update = on_update
    aggregator.on_candle_closed = on_closed
    
    # 테스트 데이터
    import time
    base_ts = int(time.time() * 1000)
    
    for i in range(10):
        candle = Candle(
            timestamp=base_ts + i * 60000,
            open=100 + i,
            high=101 + i,
            low=99 + i,
            close=100.5 + i,
            volume=100,
            is_closed=True
        )
        aggregator.process_candle(candle, '1m')
