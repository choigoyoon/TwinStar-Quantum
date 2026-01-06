"""
차트 특성 추출 모듈
- 변동성 (ATR 기반)
- 추세 강도 (RSI, 이동평균)
- 거래량 패턴
- 캔들 특성
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

# Logging
import logging
logger = logging.getLogger(__name__)


class ChartProfiler:
    """차트 프로파일 추출"""
    
    def __init__(self):
        self.profile_keys = [
            'volatility',      # 변동성
            'trend_strength',  # 추세 강도
            'volume_pattern',  # 거래량 패턴
            'price_range',     # 가격 범위
            'candle_ratio'     # 양봉/음봉 비율
        ]
    
    def extract_profile(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        DataFrame에서 차트 프로파일 추출
        
        Args:
            df: OHLCV DataFrame (columns: open, high, low, close, volume)
        
        Returns:
            프로파일 딕셔너리
        """
        if df is None or df.empty or len(df) < 20:
            return self._empty_profile()
        
        try:
            profile = {
                'volatility': self._calc_volatility(df),
                'trend_strength': self._calc_trend_strength(df),
                'volume_pattern': self._calc_volume_pattern(df),
                'price_range': self._calc_price_range(df),
                'candle_ratio': self._calc_candle_ratio(df)
            }
            return profile
        except Exception as e:
            logger.info(f"[ChartProfiler] 프로파일 추출 오류: {e}")
            return self._empty_profile()
    
    def _calc_volatility(self, df: pd.DataFrame) -> float:
        """ATR 기반 변동성 계산 (0~1 정규화)"""
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # True Range
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))[1:]
        
        # ATR (14일)
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)
        
        # 가격 대비 비율로 정규화
        avg_price = np.mean(close[-14:])
        volatility = (atr / avg_price) if avg_price > 0 else 0
        
        # 0~1 범위로 클리핑 (10% 변동성 = 1.0)
        return min(volatility / 0.1, 1.0)
    
    def _calc_trend_strength(self, df: pd.DataFrame) -> float:
        """RSI + MA 기반 추세 강도 (0~1)"""
        close = df['close'].values
        
        # RSI 계산
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else np.mean(gain)
        avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else np.mean(loss)
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # RSI를 0~1로 변환 (50 = 0.5, 극단값 = 0 or 1)
        rsi_normalized = abs(rsi - 50) / 50
        
        # MA 기울기
        if len(close) >= 20:
            ma20 = np.mean(close[-20:])
            ma5 = np.mean(close[-5:])
            ma_slope = (ma5 - ma20) / ma20 if ma20 > 0 else 0
            ma_strength = min(abs(ma_slope) / 0.05, 1.0)  # 5% 기울기 = 1.0
        else:
            ma_strength = 0.5
        
        # 평균
        return (rsi_normalized + ma_strength) / 2
    
    def _calc_volume_pattern(self, df: pd.DataFrame) -> float:
        """거래량 변화율 (0~1)"""
        if 'volume' not in df.columns:
            return 0.5
        
        volume = df['volume'].values
        if len(volume) < 20:
            return 0.5
        
        recent_vol = np.mean(volume[-5:])
        avg_vol = np.mean(volume[-20:])
        
        if avg_vol == 0:
            return 0.5
        
        ratio = recent_vol / avg_vol
        # 0.5~2.0 범위를 0~1로 매핑
        return min(max((ratio - 0.5) / 1.5, 0), 1.0)
    
    def _calc_price_range(self, df: pd.DataFrame) -> float:
        """가격 범위 (고가-저가 비율, 0~1)"""
        high = df['high'].values[-20:]
        low = df['low'].values[-20:]
        
        max_high = np.max(high)
        min_low = np.min(low)
        
        if min_low == 0:
            return 0.5
        
        range_ratio = (max_high - min_low) / min_low
        # 20% 범위 = 1.0
        return min(range_ratio / 0.2, 1.0)
    
    def _calc_candle_ratio(self, df: pd.DataFrame) -> float:
        """양봉 비율 (0~1)"""
        open_prices = df['open'].values
        close_prices = df['close'].values
        
        bullish = np.sum(close_prices > open_prices)
        total = len(close_prices)
        
        return bullish / total if total > 0 else 0.5
    
    def _empty_profile(self) -> Dict[str, float]:
        """빈 프로파일 반환"""
        return {key: 0.5 for key in self.profile_keys}
    
    def calculate_similarity(self, profile1: Dict[str, float], 
                            profile2: Dict[str, float],
                            weights: Optional[Dict[str, float]] = None) -> float:
        """
        두 프로파일 간 유사도 계산 (0~1)
        
        Args:
            profile1: 첫 번째 프로파일
            profile2: 두 번째 프로파일
            weights: 가중치 (기본: 균등)
        
        Returns:
            유사도 (1.0 = 동일)
        """
        if weights is None:
            weights = {
                'volatility': 0.30,
                'trend_strength': 0.25,
                'volume_pattern': 0.20,
                'price_range': 0.15,
                'candle_ratio': 0.10
            }
        
        total_diff = 0
        total_weight = 0
        
        for key in self.profile_keys:
            if key in profile1 and key in profile2:
                diff = abs(profile1[key] - profile2[key])
                weight = weights.get(key, 1.0)
                total_diff += diff * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        avg_diff = total_diff / total_weight
        similarity = 1.0 - avg_diff
        
        return max(0, min(similarity, 1.0))


# 테스트용
if __name__ == "__main__":
    profiler = ChartProfiler()
    
    # 더미 데이터 테스트
    dummy_df = pd.DataFrame({
        'open': np.random.uniform(100, 110, 100),
        'high': np.random.uniform(105, 115, 100),
        'low': np.random.uniform(95, 105, 100),
        'close': np.random.uniform(100, 110, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    })
    
    profile = profiler.extract_profile(dummy_df)
    logger.info(f"프로파일: {profile}")
