"""
MACD 전략
=========

MACD 히스토그램 부호 전환을 이용한 W/M 패턴 탐지

원리:
    - MACD 히스토그램이 양(+) → 음(-)으로 전환 → 고점(H) 신호
    - MACD 히스토그램이 음(-) → 양(+)으로 전환 → 저점(L) 신호
    - L-H-L 패턴 → W 패턴 → Long 진입
    - H-L-H 패턴 → M 패턴 → Short 진입

주의:
    이전에 기록된 성능 수치(승률 ~80%, +2,000%)는 극값 봉(pivot) 시점에 진입하는
    미래 데이터 누수 상태에서 측정된 값이라 무효. 진입은 신호 확정 봉 마감 기준.
"""

import numpy as np
import pandas as pd
from typing import Dict, List

from .base import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD 히스토그램 기반 W/M 패턴 전략"""
    
    name = "MACD"
    description = "MACD 히스토그램 부호 전환 기반 W/M 패턴"
    
    def detect_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """
        MACD 히스토그램 기반 W/M 패턴 탐지
        """
        tolerance = self.params.get('tolerance', 0.10)
        min_adx = self.params.get('adx_min', 10)
        min_vol_ratio = self.params.get('min_vol_ratio', 0.0)
        
        patterns = []
        macd_hist = np.asarray(df['macd_hist'].values)
        high = np.asarray(df['high'].values)
        low = np.asarray(df['low'].values)
        close = np.asarray(df['close'].values)
        adx = np.asarray(df['adx'].values)
        vol_ratio = np.asarray(df['vol_ratio'].values) if 'vol_ratio' in df.columns else np.ones(len(df))
        
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
        for i in range(segment_start + 1, n):
            if np.isnan(macd_hist[i]):
                continue
            new_sign = np.sign(macd_hist[i])
            if new_sign != current_sign and new_sign != 0:
                seg_high = high[segment_start:i]
                seg_low = low[segment_start:i]
                if len(seg_high) > 0:
                    if current_sign > 0:  # 양(+) 구간 종료 → 고점
                        max_idx = segment_start + int(np.argmax(seg_high))
                        hl_points.append({'type': 'H', 'price': float(high[max_idx]), 'pivot_idx': max_idx, 'idx': i})
                    else:  # 음(-) 구간 종료 → 저점
                        min_idx = segment_start + int(np.argmin(seg_low))
                        hl_points.append({'type': 'L', 'price': float(low[min_idx]), 'pivot_idx': min_idx, 'idx': i})
                segment_start = i
                current_sign = new_sign
        
        # W/M 패턴 매칭
        for j in range(2, len(hl_points)):
            p1, p2, p3 = hl_points[j-2], hl_points[j-1], hl_points[j]
            # 판단 시점 = 히스토그램 부호가 바뀐 봉(i)의 마감. 극값 봉(pivot_idx)은 그 시점에야 확정되므로
            # 필터/진입가는 i 기준으로만 계산한다 (pivot_idx 기준은 미래 데이터)
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
                        'swing': swing,
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
                        'swing': swing,
                    })
        
        return patterns
