"""
ADX/DI 전략 모듈
================

+DI/-DI 크로스오버를 이용한 W/M 패턴 탐지

원리:
    - Golden Cross (+DI가 -DI를 상향 돌파) → 저점(L) 신호
    - Dead Cross (-DI가 +DI를 상향 돌파) → 고점(H) 신호
    - L-H-L 패턴 → W 패턴 → Long 진입
    - H-L-H 패턴 → M 패턴 → Short 진입

성능 (1h TF, 2020~):
    - 거래: 2,572건
    - 승률: 78.8%
    - PnL: +1,938%
    - MDD: 11.1%

특징:
    - MACD 대비 거래 수가 많음 (트렌드 민감)
    - 승률은 낮지만 추세 전환을 빠르게 포착
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, cast, Optional

from ..base import BaseStrategy


class ADXDIStrategy(BaseStrategy):
    """ADX/DI 크로스오버 기반 W/M 패턴 전략"""
    
    name = "ADX/DI"
    description = "+DI/-DI 골든/데드 크로스 기반 W/M 패턴 탐지"
    
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        ADX/DI 기반 W/M 패턴 탐지
        
        Args:
            df: 지표가 계산된 데이터프레임 (plus_di, minus_di, adx 필요)
        
        Returns:
            패턴 리스트 [{'type', 'direction', 'idx', 'entry_price', 'swing'}, ...]
        """
        tolerance = self.params.get('tolerance', 0.10)
        min_adx = self.params.get('adx_min', 10)
        min_vol_ratio = self.params.get('min_vol_ratio', 0.0)
        
        patterns = []
        
        if 'plus_di' not in df.columns or 'minus_di' not in df.columns:
            return patterns
        
        plus_di = df['plus_di'].values
        minus_di = df['minus_di'].values
        adx = df['adx'].values
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        vol_ratio = df['vol_ratio'].values if 'vol_ratio' in df.columns else np.ones(len(df))
        
        hl_points = []
        
        # DI 크로스오버에서 H/L 포인트 추출
        for i in range(30, len(df) - 10):
            if np.isnan(plus_di[i-1]) or np.isnan(minus_di[i-1]):
                continue
            
            # Golden Cross (+DI > -DI) → 저점
            # +DI가 -DI를 상향 돌파 → 상승 추세 시작 → 저점 형성
            if plus_di[i-1] < minus_di[i-1] and plus_di[i] > minus_di[i]:
                window_start = max(0, i-10)
                window_low = low[window_start:i+1]
                trough_idx = window_start + np.argmin(cast(Any, window_low))
                hl_points.append({
                    'type': 'L', 
                    'idx': trough_idx,
                    'price': low[trough_idx], 
                    'bar_idx': i
                })
            
            # Dead Cross (-DI > +DI) → 고점
            # -DI가 +DI를 상향 돌파 → 하락 추세 시작 → 고점 형성
            if minus_di[i-1] < plus_di[i-1] and minus_di[i] > plus_di[i]:
                window_start = max(0, i-10)
                window_high = high[window_start:i+1]
                peak_idx = window_start + np.argmax(cast(Any, window_high))
                hl_points.append({
                    'type': 'H', 
                    'idx': peak_idx,
                    'price': high[peak_idx], 
                    'bar_idx': i
                })
        
        # W/M 패턴 매칭
        for j in range(2, len(hl_points)):
            p1, p2, p3 = hl_points[j-2], hl_points[j-1], hl_points[j]
            bar_idx = p3['bar_idx']
            idx = p3['idx']
            
            # ADX 필터
            if min_adx > 0 and (np.isnan(adx[bar_idx]) or adx[bar_idx] < min_adx):
                continue
            # Volume 필터
            if min_vol_ratio > 0 and vol_ratio[bar_idx] < min_vol_ratio:
                continue
            
            # W 패턴 (L-H-L) → Long
            if p1['type'] == 'L' and p2['type'] == 'H' and p3['type'] == 'L':
                swing = abs(p1['price'] - p3['price']) / p1['price']
                if swing <= tolerance:
                    patterns.append({
                        'type': 'W', 
                        'direction': 'Long',
                        'idx': idx, 
                        'bar_idx': bar_idx,
                        'entry_price': close[idx], 
                        'swing': swing
                    })
            
            # M 패턴 (H-L-H) → Short
            elif p1['type'] == 'H' and p2['type'] == 'L' and p3['type'] == 'H':
                swing = abs(p1['price'] - p3['price']) / p1['price']
                if swing <= tolerance:
                    patterns.append({
                        'type': 'M', 
                        'direction': 'Short',
                        'idx': idx, 
                        'bar_idx': bar_idx,
                        'entry_price': close[idx], 
                        'swing': swing
                    })
        
        return patterns


# =============================================================================
# 편의 함수
# =============================================================================
def run_adxdi_backtest(
    df: pd.DataFrame,
    params: Optional[Dict] = None,
    timeframe: str = '2h',
    apply_filters: bool = True,
) -> Dict:
    """ADX/DI 전략 백테스트 실행"""
    strategy = ADXDIStrategy(params)
    return strategy.backtest(df, timeframe, apply_filters)


def run_adxdi_optimization(
    df: pd.DataFrame,
    timeframe: str = '2h',
    mode: str = 'quick',
    apply_filters: bool = True,
    verbose: bool = True,
) -> List[Dict]:
    """ADX/DI 전략 최적화 실행"""
    strategy = ADXDIStrategy()
    return strategy.optimize(df, timeframe, mode, apply_filters, verbose)
