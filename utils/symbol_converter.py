
# Logging
import logging
logger = logging.getLogger(__name__)
"""
TwinStar Quantum - 거래소별 심볼 변환
Bybit/Binance: BTCUSDT
Upbit: KRW-BTC
Bithumb: BTC_KRW
"""

EXCHANGE_PAIR_FORMAT = {
    "bybit": "{symbol}USDT",
    "binance": "{symbol}USDT",
    "okx": "{symbol}USDT",
    "bitget": "{symbol}USDT",
    "bingx": "{symbol}USDT",
    "upbit": "KRW-{symbol}",
    "bithumb": "{symbol}_KRW",
}

EXCHANGE_QUOTE = {
    "bybit": "USDT",
    "binance": "USDT",
    "okx": "USDT",
    "bitget": "USDT",
    "bingx": "USDT",
    "upbit": "KRW",
    "bithumb": "KRW",
}

SPOT_EXCHANGES = {"upbit", "bithumb"}
KRW_EXCHANGES = {"upbit", "bithumb"}


def convert_symbol(base: str, exchange: str) -> str:
    """기본 심볼 → 거래소별 페어 변환
    
    Args:
        base: "BTC", "ETH", "BTCUSDT" 등
        exchange: "bybit", "upbit" 등
    
    Returns:
        "BTCUSDT", "KRW-BTC" 등
    """
    # 기본 심볼 추출 (BTCUSDT → BTC)
    base = extract_base(base)
    
    format_str = EXCHANGE_PAIR_FORMAT.get(exchange.lower())
    if format_str:
        return format_str.format(symbol=base)
    
    return f"{base}USDT"


def extract_base(pair: str) -> str:
    """거래소 페어 → 기본 심볼 추출
    
    Args:
        pair: "BTCUSDT", "KRW-BTC", "BTC_KRW", "BTC" 등
    
    Returns:
        "BTC"
    """
    if not pair:
        return ""
    
    pair = pair.upper().strip()
    
    # USDT 페어
    if pair.endswith("USDT"):
        return pair[:-4]
    
    # BUSD 페어
    if pair.endswith("BUSD"):
        return pair[:-4]
    
    # USDC 페어
    if pair.endswith("USDC"):
        return pair[:-4]
    
    # Upbit (KRW-BTC)
    if pair.startswith("KRW-"):
        return pair[4:]
    
    # Bithumb (BTC_KRW)
    if pair.endswith("_KRW"):
        return pair[:-4]
    
    # 이미 기본 심볼
    return pair


def is_krw_exchange(exchange: str) -> bool:
    """KRW 거래소 여부"""
    return exchange.lower() in KRW_EXCHANGES


def is_spot_exchange(exchange: str) -> bool:
    """현물 전용 거래소 여부"""
    return exchange.lower() in SPOT_EXCHANGES


def get_quote_currency(exchange: str) -> str:
    """거래소별 기준 통화"""
    return EXCHANGE_QUOTE.get(exchange.lower(), "USDT")


def normalize_symbol_for_storage(pair: str) -> str:
    """저장용 심볼 정규화 (파일명용)
    
    Args:
        pair: "BTCUSDT", "KRW-BTC" 등
    
    Returns:
        "btcusdt" (소문자, 특수문자 제거)
    """
    return pair.lower().replace("-", "").replace("_", "")


def get_display_symbol(base: str, exchange: str) -> tuple:
    """UI 표시용 (기본심볼, 페어)
    
    Returns:
        ("BTC", "BTCUSDT") or ("BTC", "KRW-BTC")
    """
    base = extract_base(base)
    pair = convert_symbol(base, exchange)
    return (base, pair)


def convert_all_symbols(symbols: list, from_exchange: str, to_exchange: str) -> list:
    """심볼 목록 일괄 변환
    
    Args:
        symbols: ["BTCUSDT", "ETHUSDT"]
        from_exchange: "bybit"
        to_exchange: "upbit"
    
    Returns:
        ["KRW-BTC", "KRW-ETH"]
    """
    result = []
    for sym in symbols:
        base = extract_base(sym)
        converted = convert_symbol(base, to_exchange)
        result.append(converted)
    return result


# 테스트용
if __name__ == "__main__":
    logger.info("=== Symbol Converter Test ===")
    
    # 기본 변환
    logger.info(f"BTC → bybit: {convert_symbol('BTC', 'bybit')}")
    logger.info(f"BTC → upbit: {convert_symbol('BTC', 'upbit')}")
    logger.info(f"BTC → bithumb: {convert_symbol('BTC', 'bithumb')}")
    
    # 역변환
    logger.info(f"BTCUSDT → base: {extract_base('BTCUSDT')}")
    logger.info(f"KRW-BTC → base: {extract_base('KRW-BTC')}")
    logger.info(f"BTC_KRW → base: {extract_base('BTC_KRW')}")
    
    # 거래소 체크
    logger.info(f"upbit is KRW: {is_krw_exchange('upbit')}")
    logger.info(f"bybit is KRW: {is_krw_exchange('bybit')}")
    
    # 일괄 변환
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    logger.info(f"bybit → upbit: {convert_all_symbols(symbols, 'bybit', 'upbit')}")
