# utils/time_utils.py
"""
시간 유틸리티 - 거래소별 시간대 처리
- 거래소별 시간대 상수
- UTC/KST 변환 함수
- 통일된 시간 비교 함수
"""

from datetime import datetime, timedelta, timezone

# Logging
import logging
logger = logging.getLogger(__name__)

# ========== 시간대 상수 ==========
UTC = timezone.utc
KST = timezone(timedelta(hours=9))

# ========== 거래소별 시간대 ==========
EXCHANGE_TIMEZONE = {
    # 선물 거래소 (UTC)
    'bybit': UTC,
    'binance': UTC,
    'okx': UTC,
    'bitget': UTC,
    'bingx': UTC,
    'lighter': UTC,
    
    # 국내 거래소 (KST)
    'bithumb': KST,
    'upbit': KST,
}


def get_exchange_tz(exchange: str) -> timezone:
    """거래소 시간대 반환"""
    return EXCHANGE_TIMEZONE.get(exchange.lower(), UTC)


def get_exchange_now(exchange: str) -> datetime:
    """
    거래소 기준 현재 시간 (timezone-aware)
    
    Args:
        exchange: 거래소 이름 (bybit, binance, bithumb, upbit 등)
        
    Returns:
        datetime: 거래소 시간대의 현재 시간
    """
    tz = get_exchange_tz(exchange)
    return datetime.now(tz)


def get_utc_now() -> datetime:
    """UTC 현재 시간 (timezone-aware)"""
    return datetime.now(UTC)


def get_kst_now() -> datetime:
    """KST 현재 시간 (timezone-aware)"""
    return datetime.now(KST)


def to_utc(dt: datetime, exchange: str = None) -> datetime:
    """
    datetime을 UTC로 변환
    
    Args:
        dt: 변환할 datetime
        exchange: 거래소 이름 (dt가 naive인 경우 이 거래소의 시간대로 가정)
        
    Returns:
        datetime: UTC 시간
    """
    # 이미 timezone-aware인 경우
    if dt.tzinfo is not None:
        return dt.astimezone(UTC)
    
    # naive datetime인 경우 거래소 시간대 가정
    if exchange:
        tz = get_exchange_tz(exchange)
        dt = dt.replace(tzinfo=tz)
        return dt.astimezone(UTC)
    
    # 기본값: UTC로 가정
    return dt.replace(tzinfo=UTC)


def to_kst(dt: datetime, exchange: str = None) -> datetime:
    """
    datetime을 KST로 변환
    
    Args:
        dt: 변환할 datetime
        exchange: 거래소 이름 (dt가 naive인 경우 이 거래소의 시간대로 가정)
        
    Returns:
        datetime: KST 시간
    """
    if dt.tzinfo is not None:
        return dt.astimezone(KST)
    
    if exchange:
        tz = get_exchange_tz(exchange)
        dt = dt.replace(tzinfo=tz)
        return dt.astimezone(KST)
    
    return dt.replace(tzinfo=UTC).astimezone(KST)


def hours_since(dt: datetime, exchange: str = None) -> float:
    """
    주어진 시간부터 현재까지 경과 시간 (시간 단위)
    
    Args:
        dt: 시작 시간
        exchange: 거래소 이름 (naive datetime인 경우 시간대 추정용)
        
    Returns:
        float: 경과 시간 (hours)
    """
    if exchange:
        now = get_exchange_now(exchange)
        dt_tz = to_utc(dt, exchange)
        now_utc = to_utc(now, exchange)
    else:
        now_utc = get_utc_now()
        dt_tz = to_utc(dt)
    
    return (now_utc - dt_tz).total_seconds() / 3600


def is_signal_valid(signal_time: datetime, validity_hours: float, exchange: str = None) -> bool:
    """
    시그널 유효성 검사
    
    Args:
        signal_time: 시그널 생성 시간
        validity_hours: 유효 시간 (hours)
        exchange: 거래소 이름
        
    Returns:
        bool: 유효 여부
    """
    elapsed = hours_since(signal_time, exchange)
    return elapsed <= validity_hours


def format_for_log(dt: datetime = None, tz: timezone = None) -> str:
    """
    로그용 시간 문자열 포맷
    
    Args:
        dt: datetime (None이면 현재 시간)
        tz: 시간대 (None이면 KST)
        
    Returns:
        str: "YYYY-MM-DD HH:MM:SS" 형식
    """
    tz = tz or KST
    if dt is None:
        dt = datetime.now(tz)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC).astimezone(tz)
    else:
        dt = dt.astimezone(tz)
    
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def format_iso(dt: datetime = None) -> str:
    """
    ISO 8601 형식 문자열
    
    Args:
        dt: datetime (None이면 현재 UTC 시간)
        
    Returns:
        str: ISO 8601 형식
    """
    if dt is None:
        dt = get_utc_now()
    return dt.isoformat()


# ========== 테스트 ==========
if __name__ == "__main__":
    logger.info("=== Time Utils Test ===")
    
    logger.info(f"\nUTC Now: {get_utc_now()}")
    logger.info(f"KST Now: {get_kst_now()}")
    
    logger.info(f"\nBybit Now: {get_exchange_now('bybit')}")
    logger.info(f"Upbit Now: {get_exchange_now('upbit')}")
    
    # 시그널 유효성 테스트
    test_signal = get_utc_now() - timedelta(hours=3)
    logger.info(f"\n3시간 전 시그널 (4시간 유효): {is_signal_valid(test_signal, 4)}")
    logger.info(f"3시간 전 시그널 (2시간 유효): {is_signal_valid(test_signal, 2)}")
    
    logger.info(f"\nLog Format: {format_for_log()}")
    logger.info(f"ISO Format: {format_iso()}")
