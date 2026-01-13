"""
타임프레임 관련 상수
"""

from typing import List

# ============ 지원 타임프레임 ============
TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w']

# ============ Trend TF → Entry TF 매핑 ============
TF_MAPPING = {
    '15m': '5m',
    '30m': '15m',
    '1h': '15m',
    '2h': '30m',
    '4h': '1h',
    '6h': '2h',
    '12h': '4h',
    '1d': '4h',
    '1w': '1d'
}

# ============ Pandas 리샘플링 매핑 ============
TF_RESAMPLE_MAP = {
    # 분
    '1m': '1min', '1min': '1min',
    '5m': '5min', '5min': '5min',
    '15m': '15min', '15min': '15min',
    '30m': '30min', '30min': '30min',
    '45m': '45min', '45min': '45min',
    # 시간
    '1h': '1h', '1H': '1h',
    '2h': '2h', '2H': '2h',
    '3h': '3h', '3H': '3h',
    '4h': '4h', '4H': '4h',
    '6h': '6h', '6H': '6h',
    '12h': '12h', '12H': '12h',
    # 일/주
    '1d': '1D', '1D': '1D',
    '1w': 'W-MON', '1W': 'W-MON'
}

# ============ 타임프레임 → 분 변환 ============
TF_TO_MINUTES = {
    '1m': 1, '5m': 5, '15m': 15, '30m': 30, '45m': 45,
    '1h': 60, '2h': 120, '3h': 180, '4h': 240, '6h': 360, '12h': 720,
    '1d': 1440, '1w': 10080
}


# ============ 헬퍼 함수 ============

def normalize_timeframe(tf: str) -> str:
    """
    타임프레임 정규화
    
    Examples:
        '15min' -> '15m'
        '1H' -> '1h'
        '1D' -> '1d'
    """
    tf_lower = tf.lower()
    
    # 'min' 접미사 처리
    if 'min' in tf_lower:
        num = tf_lower.replace('min', '')
        return f"{num}m"
    
    # 대문자 처리
    if tf[-1].isupper():
        return tf.lower()
    
    return tf


def get_entry_tf(trend_tf: str) -> str:
    """
    트렌드 타임프레임에 대응하는 진입 타임프레임 반환
    
    Args:
        trend_tf: 트렌드 타임프레임 (예: '4h')
    
    Returns:
        진입 타임프레임 (예: '1h')
    """
    normalized = normalize_timeframe(trend_tf)
    return TF_MAPPING.get(normalized, '15m')


def get_resample_rule(tf: str) -> str:
    """
    Pandas 리샘플링 규칙 반환
    
    Args:
        tf: 타임프레임
    
    Returns:
        Pandas 리샘플링 규칙 문자열
    """
    normalized = normalize_timeframe(tf)
    return TF_RESAMPLE_MAP.get(normalized, TF_RESAMPLE_MAP.get(tf, '1h'))


def tf_to_minutes(tf: str) -> int:
    """
    타임프레임을 분 단위로 변환
    
    Args:
        tf: 타임프레임 (예: '4h')
    
    Returns:
        분 단위 (예: 240)
    """
    normalized = normalize_timeframe(tf)
    return TF_TO_MINUTES.get(normalized, 60)


def minutes_to_tf(minutes: int) -> str:
    """
    분을 타임프레임으로 변환
    
    Args:
        minutes: 분 단위
    
    Returns:
        타임프레임 문자열
    """
    for tf, mins in TF_TO_MINUTES.items():
        if mins == minutes:
            return tf
    return '1h'


def get_higher_timeframes(tf: str) -> List[str]:
    """
    주어진 타임프레임보다 높은 타임프레임 목록 반환
    """
    minutes = tf_to_minutes(tf)
    return [t for t in TIMEFRAMES if tf_to_minutes(t) > minutes]


def get_lower_timeframes(tf: str) -> List[str]:
    """
    주어진 타임프레임보다 낮은 타임프레임 목록 반환
    """
    minutes = tf_to_minutes(tf)
    return [t for t in TIMEFRAMES if tf_to_minutes(t) < minutes]
