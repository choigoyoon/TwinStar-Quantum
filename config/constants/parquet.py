"""
config/constants/parquet.py
Parquet 파일명 규칙 (SSOT) - Phase A-3

규칙: {exchange}_{symbol}_{timeframe}.parquet
- 모두 소문자 강제
- 특수문자 제거 (심볼)
"""


def normalize_exchange(exchange: str) -> str:
    """거래소 이름 → 소문자"""
    return exchange.strip().lower()


def normalize_symbol(symbol: str) -> str:
    """심볼 → 소문자 + 특수문자 제거"""
    return symbol.strip().lower().replace('/', '').replace(':', '').replace('-', '').replace('_', '')


def normalize_timeframe(timeframe: str) -> str:
    """타임프레임 → 소문자 (15m, 1h, 4h, 1d)"""
    return timeframe.strip().lower()


def get_parquet_filename(exchange: str, symbol: str, timeframe: str) -> str:
    """
    Parquet 파일명 생성

    Examples:
        ('Bybit', 'BTC/USDT', '15m') → 'bybit_btcusdt_15m.parquet'
        ('BINANCE', 'ETH-USDT', '1H') → 'binance_ethusdt_1h.parquet'
    """
    return f"{normalize_exchange(exchange)}_{normalize_symbol(symbol)}_{normalize_timeframe(timeframe)}.parquet"
