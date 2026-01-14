"""
날짜/시간 포맷팅 유틸리티
"""

from datetime import datetime, timedelta
from typing import Union, Optional


def format_datetime(dt: Union[datetime, str, int, float, None], 
                    fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    날짜시간 포맷팅
    
    Args:
        dt: datetime 객체, ISO 문자열, 또는 타임스탬프
        fmt: 출력 포맷
    
    Returns:
        포맷된 문자열
    
    Examples:
        format_datetime(datetime.now()) -> '2026-01-13 10:30:45'
    """
    if dt is None:
        return '-'
    
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        elif isinstance(dt, (int, float)):
            # 타임스탬프 (밀리초 또는 초)
            if dt > 1e12:  # 밀리초
                dt = datetime.fromtimestamp(dt / 1000)
            else:
                dt = datetime.fromtimestamp(dt)
        
        return dt.strftime(fmt)
    except (ValueError, TypeError, OSError):
        return '-'


def format_date(dt: Union[datetime, str, int, float, None], 
                fmt: str = '%Y-%m-%d') -> str:
    """날짜 포맷팅"""
    return format_datetime(dt, fmt)


def format_time(dt: Union[datetime, str, int, float, None], 
                fmt: str = '%H:%M:%S') -> str:
    """시간 포맷팅"""
    return format_datetime(dt, fmt)


def format_duration(seconds: Union[int, float, None]) -> str:
    """
    시간 간격 포맷팅
    
    Args:
        seconds: 초 단위 시간
    
    Returns:
        포맷된 문자열
    
    Examples:
        format_duration(3661) -> '1h 1m 1s'
        format_duration(86400) -> '1d 0h 0m'
        format_duration(45) -> '45s'
    """
    if seconds is None:
        return '-'
    
    try:
        seconds = int(seconds)
        
        if seconds < 0:
            return '-'
        
        if seconds < 60:
            return f"{seconds}s"
        
        minutes = seconds // 60
        secs = seconds % 60
        
        if minutes < 60:
            return f"{minutes}m {secs}s"
        
        hours = minutes // 60
        mins = minutes % 60
        
        if hours < 24:
            return f"{hours}h {mins}m {secs}s"
        
        days = hours // 24
        hrs = hours % 24
        
        return f"{days}d {hrs}h {mins}m"
    
    except (TypeError, ValueError):
        return '-'


def format_relative_time(dt: Union[datetime, str, int, float, None]) -> str:
    """
    상대 시간 포맷팅 ('3분 전', '1시간 후' 등)
    
    Args:
        dt: 비교할 시간
    
    Returns:
        상대 시간 문자열
    
    Examples:
        format_relative_time(datetime.now() - timedelta(minutes=5)) -> '5분 전'
        format_relative_time(datetime.now() + timedelta(hours=2)) -> '2시간 후'
    """
    if dt is None:
        return '-'
    
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        elif isinstance(dt, (int, float)):
            if dt > 1e12:
                dt = datetime.fromtimestamp(dt / 1000)
            else:
                dt = datetime.fromtimestamp(dt)
        
        now = datetime.now()
        diff = now - dt
        
        total_seconds = int(diff.total_seconds())
        abs_seconds = abs(total_seconds)
        
        # 미래/과거 결정
        suffix = '전' if total_seconds > 0 else '후'
        
        if abs_seconds < 60:
            return f"{abs_seconds}초 {suffix}"
        elif abs_seconds < 3600:
            minutes = abs_seconds // 60
            return f"{minutes}분 {suffix}"
        elif abs_seconds < 86400:
            hours = abs_seconds // 3600
            return f"{hours}시간 {suffix}"
        elif abs_seconds < 604800:
            days = abs_seconds // 86400
            return f"{days}일 {suffix}"
        elif abs_seconds < 2592000:
            weeks = abs_seconds // 604800
            return f"{weeks}주 {suffix}"
        elif abs_seconds < 31536000:
            months = abs_seconds // 2592000
            return f"{months}개월 {suffix}"
        else:
            years = abs_seconds // 31536000
            return f"{years}년 {suffix}"
    
    except (ValueError, TypeError, OSError):
        return '-'


def format_timestamp(ts: Union[int, float, None], ms: bool = False) -> str:
    """
    타임스탬프 포맷팅
    
    Args:
        ts: 타임스탬프
        ms: 밀리초 단위 여부
    
    Returns:
        포맷된 날짜시간 문자열
    """
    if ts is None:
        return '-'
    
    try:
        if ms or ts > 1e12:
            ts = ts / 1000
        
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError):
        return '-'


def get_kst_now() -> datetime:
    """한국 시간 반환 (UTC+9)"""
    return datetime.utcnow() + timedelta(hours=9)


def get_utc_now() -> datetime:
    """UTC 시간 반환"""
    return datetime.utcnow()


def to_timestamp(dt: datetime, ms: bool = True) -> int:
    """
    datetime을 타임스탬프로 변환
    
    Args:
        dt: datetime 객체
        ms: 밀리초 단위 여부
    
    Returns:
        타임스탬프
    """
    ts = dt.timestamp()
    if ms:
        return int(ts * 1000)
    return int(ts)
