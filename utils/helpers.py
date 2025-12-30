# utils/helpers.py
"""공통 헬퍼 함수 모음"""


def safe_float(value, default=0.0):
    """
    dict, None, str 등을 안전하게 float로 변환
    
    사용 예:
        balance = safe_float(exchange.get_balance("KRW"))
        size = safe_float(position.get('size'))
    
    Args:
        value: 변환할 값 (float, dict, str, None 등)
        default: 변환 실패 시 반환할 기본값
    
    Returns:
        float: 변환된 값 또는 기본값
    """
    if value is None:
        return default
    
    if isinstance(value, dict):
        # ccxt / pybithumb / pyupbit 등 다양한 형식 지원
        return float(
            value.get('free', 
            value.get('total', 
            value.get('available', 
            value.get('balance', default))))
        )
    
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    """안전한 int 변환"""
    if value is None:
        return default
    if isinstance(value, dict):
        return int(safe_float(value, default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
