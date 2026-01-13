"""
MACD 전략 모듈
==============

MACD 히스토그램 부호 전환을 이용한 W/M 패턴 탐지

원리:
    - MACD 히스토그램이 양(+) → 음(-)으로 전환되면 고점(H) 신호
    - MACD 히스토그램이 음(-) → 양(+)으로 전환되면 저점(L) 신호
    - L-H-L 패턴 → W 패턴 → Long 진입
    - H-L-H 패턴 → M 패턴 → Short 진입

성능 (1h TF, 2020~):
    - 거래: 2,216건
    - 승률: 83.8%
    - PnL: +2,077%
    - MDD: 10.9%
"""

import numpy as np
import pandas as pd
from typing import Dict, List

from ..base import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD 히스토그램 기반 W/M 패턴 전략"""
    
    name = "MACD"
    description = "MACD 히스토그램 부호 전환 기반 W/M 패턴 탐지"
    
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        MACD 히스토그램 기반 W/M 패턴 탐지
        
        Args:
            df: 지표가 계산된 데이터프레임 (macd_hist, adx, vol_ratio 필요)
        
        Returns:
            패턴 리스트 [{'type', 'direction', 'idx', 'entry_price', 'swing'}, ...]
        """
        tolerance = self.params.get('tolerance', 0.10)
        min_adx = self.params.get('adx_min', 10)
        min_vol_ratio = self.params.get('min_vol_ratio', 0.0)
        
        patterns = []
        macd_hist = df['macd_hist'].values
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        adx = df['adx'].values
        vol_ratio = df['vol_ratio'].values if 'vol_ratio' in df.columns else np.ones(len(df))
        
        n = len(macd_hist)
        hl_points = []
        
        # 첫 유효한 신호 찾기
        segment_start = 0
        current_sign = 0
        for i in range(n):
            if not np.isnan(macd_hist[i]):
                current_sign = np.sign(macd_hist[i])
                segment_start = i
                break
        
        # H/L 포인트 추출
        # - MACD 히스토그램이 양(+) 구간에서 최고점 → H (고점)
        # - MACD 히스토그램이 음(-) 구간에서 최저점 → L (저점)
        for i in range(segment_start + 1, n):
            if np.isnan(macd_hist[i]):
                continue
            new_sign = np.sign(macd_hist[i])
            if new_sign != current_sign and new_sign != 0:
                seg_high = high[segment_start:i]
                seg_low = low[segment_start:i]
                if len(seg_high) > 0:
                    if current_sign > 0:  # 양(+) 구간 종료 → 고점
                        max_idx = segment_start + np.argmax(seg_high)
                        hl_points.append({'type': 'H', 'price': high[max_idx], 'idx': max_idx})
                    else:  # 음(-) 구간 종료 → 저점
                        min_idx = segment_start + np.argmin(seg_low)
                        hl_points.append({'type': 'L', 'price': low[min_idx], 'idx': min_idx})
                segment_start = i
                current_sign = new_sign
        
        # W/M 패턴 매칭
        for j in range(2, len(hl_points)):
            p1, p2, p3 = hl_points[j-2], hl_points[j-1], hl_points[j]
            idx = p3['idx']
            
            # ADX 필터
            if min_adx > 0 and (np.isnan(adx[idx]) or adx[idx] < min_adx):
                continue
            # Volume 필터
            if min_vol_ratio > 0 and vol_ratio[idx] < min_vol_ratio:
                continue
            
            # W 패턴 (L-H-L) → Long
            if p1['type'] == 'L' and p2['type'] == 'H' and p3['type'] == 'L':
                swing = abs(p1['price'] - p3['price']) / min(p1['price'], p3['price'])
                if swing <= tolerance:
                    patterns.append({
                        'type': 'W', 
                        'direction': 'Long', 
                        'idx': idx,
                        'entry_price': close[idx], 
                        'swing': swing
                    })
            
            # M 패턴 (H-L-H) → Short
            elif p1['type'] == 'H' and p2['type'] == 'L' and p3['type'] == 'H':
                swing = abs(p1['price'] - p3['price']) / min(p1['price'], p3['price'])
                if swing <= tolerance:
                    patterns.append({
                        'type': 'M', 
                        'direction': 'Short', 
                        'idx': idx,
                        'entry_price': close[idx], 
                        'swing': swing
                    })
        
        return patterns


# =============================================================================
# 편의 함수
# =============================================================================
def run_macd_backtest(
    df: pd.DataFrame,
    params: Dict = None,
    timeframe: str = '2h',
    apply_filters: bool = True,
) -> Dict:
    """MACD 전략 백테스트 실행"""
    strategy = MACDStrategy(params)
    return strategy.backtest(df, timeframe, apply_filters)


def run_macd_optimization(
    df: pd.DataFrame,
    timeframe: str = '2h',
    mode: str = 'quick',
    apply_filters: bool = True,
    verbose: bool = True,
) -> List[Dict]:
    """MACD 전략 최적화 실행"""
    strategy = MACDStrategy()
    return strategy.optimize(df, timeframe, mode, apply_filters, verbose)
