"""
필터 모듈
=========

진입 신호 필터링 로직
- Stochastic 필터: 과매수/과매도 영역에서 진입 방지
- Downtrend 필터: 하락 추세에서 Short만 허용
"""

from typing import Dict, Tuple


def apply_entry_filters(
    direction: str,
    stoch_k: float,
    downtrend: bool,
    params: Dict,
) -> Tuple[bool, str, Dict[str, int]]:
    """
    진입 필터 적용
    
    Args:
        direction: 'Long' or 'Short'
        stoch_k: Stochastic K 값
        downtrend: 하락 추세 여부
        params: 파라미터 딕셔너리
    
    Returns:
        (통과 여부, 필터 이유, 필터된 카운트)
    """
    stoch_long_max = params.get('stoch_long_max', 50)
    stoch_short_min = params.get('stoch_short_min', 50)
    use_downtrend_filter = params.get('use_downtrend_filter', True)
    
    counts = {'stoch': 0, 'downtrend': 0}
    
    # Stochastic 필터
    if direction == 'Long' and stoch_long_max < 100:
        if stoch_k > stoch_long_max:
            counts['stoch'] = 1
            return False, 'stoch_filter', counts
    
    if direction == 'Short' and stoch_short_min > 0:
        if stoch_k < stoch_short_min:
            counts['stoch'] = 1
            return False, 'stoch_filter', counts
    
    # Downtrend 필터 (Short만)
    if use_downtrend_filter and direction == 'Short':
        if not downtrend:
            counts['downtrend'] = 1
            return False, 'downtrend_filter', counts
    
    return True, '', counts
