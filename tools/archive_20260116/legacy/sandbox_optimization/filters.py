"""
필터 모듈
=========

진입 신호 필터링 로직 분리
- Stochastic 필터
- Downtrend 필터
- ADX 필터
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional


class SignalFilter:
    """
    진입 신호 필터 클래스
    
    사용법:
        filter = SignalFilter(params)
        should_enter, reason = filter.check(direction, idx, df_values)
    """
    
    def __init__(self, params: Dict[str, Any]):
        self.stoch_long_max = params.get('stoch_long_max', 50)
        self.stoch_short_min = params.get('stoch_short_min', 50)
        self.use_downtrend_filter = params.get('use_downtrend_filter', True)
        self.adx_min = params.get('adx_min', 10)
        
        # 필터 통계
        self.filtered_count = {
            'stoch': 0,
            'downtrend': 0,
            'adx': 0,
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self.filtered_count = {'stoch': 0, 'downtrend': 0, 'adx': 0}
    
    def check_stochastic(self, direction: str, stoch_k: float) -> Tuple[bool, str]:
        """
        Stochastic 필터
        - Long: stoch_k <= stoch_long_max (기본 50) 일 때만 진입
        - Short: stoch_k >= stoch_short_min (기본 50) 일 때만 진입
        """
        if np.isnan(stoch_k):
            return True, ''
        
        if direction == 'Long' and self.stoch_long_max < 100:
            if stoch_k > self.stoch_long_max:
                self.filtered_count['stoch'] += 1
                return False, f'Stoch {stoch_k:.1f} > {self.stoch_long_max}'
        
        if direction == 'Short' and self.stoch_short_min > 0:
            if stoch_k < self.stoch_short_min:
                self.filtered_count['stoch'] += 1
                return False, f'Stoch {stoch_k:.1f} < {self.stoch_short_min}'
        
        return True, ''
    
    def check_downtrend(self, direction: str, is_downtrend: bool) -> Tuple[bool, str]:
        """
        Downtrend 필터
        - Short: EMA21 < EMA50 (하락추세) 일 때만 진입
        """
        if not self.use_downtrend_filter:
            return True, ''
        
        if direction == 'Short' and not is_downtrend:
            self.filtered_count['downtrend'] += 1
            return False, 'Not downtrend'
        
        return True, ''
    
    def check_adx(self, adx_value: float) -> Tuple[bool, str]:
        """
        ADX 필터
        - ADX >= adx_min 일 때만 진입
        """
        if np.isnan(adx_value):
            return True, ''
        
        if adx_value < self.adx_min:
            self.filtered_count['adx'] += 1
            return False, f'ADX {adx_value:.1f} < {self.adx_min}'
        
        return True, ''
    
    def check_all(
        self,
        direction: str,
        stoch_k: float,
        is_downtrend: bool,
        adx_value: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        모든 필터 체크
        
        Returns:
            (통과 여부, 필터링 사유)
        """
        # Stochastic 필터
        passed, reason = self.check_stochastic(direction, stoch_k)
        if not passed:
            return False, reason
        
        # Downtrend 필터
        passed, reason = self.check_downtrend(direction, is_downtrend)
        if not passed:
            return False, reason
        
        # ADX 필터 (옵션)
        if adx_value is not None:
            passed, reason = self.check_adx(adx_value)
            if not passed:
                return False, reason
        
        return True, ''
    
    def get_stats(self) -> Dict[str, int]:
        """필터 통계 반환"""
        return self.filtered_count.copy()


def apply_filters(
    direction: str,
    stoch_k: float,
    is_downtrend: bool,
    params: Dict[str, Any],
    adx_value: Optional[float] = None
) -> Tuple[bool, str]:
    """
    함수형 인터페이스 (클래스 없이 사용)
    
    사용법:
        passed, reason = apply_filters('Long', 45.0, False, params)
    """
    stoch_long_max = params.get('stoch_long_max', 50)
    stoch_short_min = params.get('stoch_short_min', 50)
    use_downtrend_filter = params.get('use_downtrend_filter', True)
    adx_min = params.get('adx_min', 10)
    
    # Stochastic 필터
    if not np.isnan(stoch_k):
        if direction == 'Long' and stoch_long_max < 100:
            if stoch_k > stoch_long_max:
                return False, f'Stoch {stoch_k:.1f} > {stoch_long_max}'
        if direction == 'Short' and stoch_short_min > 0:
            if stoch_k < stoch_short_min:
                return False, f'Stoch {stoch_k:.1f} < {stoch_short_min}'
    
    # Downtrend 필터
    if use_downtrend_filter and direction == 'Short':
        if not is_downtrend:
            return False, 'Not downtrend'
    
    # ADX 필터
    if adx_value is not None and not np.isnan(adx_value):
        if adx_value < adx_min:
            return False, f'ADX {adx_value:.1f} < {adx_min}'
    
    return True, ''
