"""
숫자 포맷팅 유틸리티
"""

from typing import Union, Optional


def format_number(value: Union[int, float], decimals: int = 2, 
                  thousand_sep: bool = True) -> str:
    """
    숫자 포맷팅
    
    Args:
        value: 포맷할 숫자
        decimals: 소수점 자릿수
        thousand_sep: 천단위 구분자 사용 여부
    
    Returns:
        포맷된 문자열
    
    Examples:
        format_number(1234567.89) -> '1,234,567.89'
        format_number(1234567.89, decimals=0) -> '1,234,568'
    """
    if value is None:
        return '-'
    
    try:
        if thousand_sep:
            return f"{float(value):,.{decimals}f}"
        else:
            return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return '-'


def format_currency(value: Union[int, float], currency: str = 'USDT',
                    decimals: int = 2) -> str:
    """
    통화 포맷팅
    
    Args:
        value: 금액
        currency: 통화 단위
        decimals: 소수점 자릿수
    
    Returns:
        포맷된 통화 문자열
    
    Examples:
        format_currency(1234.56) -> '$1,234.56'
        format_currency(1234.56, 'KRW', 0) -> '₩1,235'
    """
    if value is None:
        return '-'
    
    try:
        formatted = format_number(value, decimals)
        
        if currency.upper() in ('USD', 'USDT', 'USDC'):
            return f"${formatted}"
        elif currency.upper() == 'KRW':
            return f"₩{formatted}"
        elif currency.upper() in ('BTC',):
            return f"₿{formatted}"
        elif currency.upper() in ('ETH',):
            return f"Ξ{formatted}"
        else:
            return f"{formatted} {currency}"
    except (TypeError, ValueError):
        return '-'


def format_percent(value: Union[int, float], decimals: int = 2,
                   include_sign: bool = True) -> str:
    """
    퍼센트 포맷팅
    
    Args:
        value: 비율 (0.05 = 5%)
        decimals: 소수점 자릿수
        include_sign: 부호 포함 여부
    
    Returns:
        포맷된 퍼센트 문자열
    
    Examples:
        format_percent(0.05) -> '+5.00%'
        format_percent(-0.12) -> '-12.00%'
    """
    if value is None:
        return '-'
    
    try:
        pct = float(value) * 100
        
        if include_sign and pct > 0:
            return f"+{pct:.{decimals}f}%"
        else:
            return f"{pct:.{decimals}f}%"
    except (TypeError, ValueError):
        return '-'


def format_pnl(value: Union[int, float], currency: str = 'USDT',
               decimals: int = 2) -> str:
    """
    손익 포맷팅 (부호 포함)
    
    Args:
        value: 손익 금액
        currency: 통화 단위
        decimals: 소수점 자릿수
    
    Returns:
        포맷된 손익 문자열
    
    Examples:
        format_pnl(123.45) -> '+$123.45'
        format_pnl(-50.00) -> '-$50.00'
    """
    if value is None:
        return '-'
    
    try:
        abs_value = abs(float(value))
        formatted = format_number(abs_value, decimals)
        
        if currency.upper() in ('USD', 'USDT', 'USDC'):
            symbol = '$'
        elif currency.upper() == 'KRW':
            symbol = '₩'
        else:
            symbol = ''
        
        if value >= 0:
            return f"+{symbol}{formatted}"
        else:
            return f"-{symbol}{formatted}"
    except (TypeError, ValueError):
        return '-'


def format_price(value: Union[int, float], decimals: Optional[int] = None) -> str:
    """
    가격 포맷팅 (자동 소수점 결정)
    
    Args:
        value: 가격
        decimals: 소수점 자릿수 (None이면 자동)
    
    Returns:
        포맷된 가격 문자열
    """
    if value is None:
        return '-'
    
    try:
        v = float(value)
        
        if decimals is None:
            # 자동 소수점 결정
            if v >= 1000:
                decimals = 2
            elif v >= 1:
                decimals = 4
            elif v >= 0.01:
                decimals = 6
            else:
                decimals = 8
        
        return format_number(v, decimals)
    except (TypeError, ValueError):
        return '-'


def format_volume(value: Union[int, float]) -> str:
    """
    거래량 포맷팅 (자동 단위)
    
    Args:
        value: 거래량
    
    Returns:
        포맷된 거래량 문자열
    
    Examples:
        format_volume(1234567) -> '1.23M'
        format_volume(12345) -> '12.35K'
    """
    return abbreviate_number(value)


def format_with_sign(value: Union[int, float], decimals: int = 2) -> str:
    """
    부호 포함 숫자 포맷팅
    
    Args:
        value: 숫자
        decimals: 소수점 자릿수
    
    Returns:
        부호 포함 문자열
    """
    if value is None:
        return '-'
    
    try:
        v = float(value)
        formatted = format_number(abs(v), decimals)
        
        if v > 0:
            return f"+{formatted}"
        elif v < 0:
            return f"-{formatted}"
        else:
            return formatted
    except (TypeError, ValueError):
        return '-'


def abbreviate_number(value: Union[int, float], decimals: int = 2) -> str:
    """
    큰 숫자 축약 (K, M, B)
    
    Args:
        value: 숫자
        decimals: 소수점 자릿수
    
    Returns:
        축약된 문자열
    
    Examples:
        abbreviate_number(1234567890) -> '1.23B'
        abbreviate_number(1234567) -> '1.23M'
        abbreviate_number(12345) -> '12.35K'
        abbreviate_number(123) -> '123.00'
    """
    if value is None:
        return '-'
    
    try:
        v = float(value)
        abs_v = abs(v)
        sign = '-' if v < 0 else ''
        
        if abs_v >= 1_000_000_000:
            return f"{sign}{abs_v / 1_000_000_000:.{decimals}f}B"
        elif abs_v >= 1_000_000:
            return f"{sign}{abs_v / 1_000_000:.{decimals}f}M"
        elif abs_v >= 1_000:
            return f"{sign}{abs_v / 1_000:.{decimals}f}K"
        else:
            return f"{sign}{abs_v:.{decimals}f}"
    except (TypeError, ValueError):
        return '-'
