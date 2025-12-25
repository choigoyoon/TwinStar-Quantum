# exchanges/__init__.py
"""
거래소 어댑터 모듈
"""

from .base_exchange import BaseExchange, Position, Signal

# 거래소별 어댑터 (lazy import 가능)
__all__ = [
    'BaseExchange', 
    'Position', 
    'Signal',
    'BybitExchange',
    'BinanceExchange',
    'LighterExchange',
    'CCXTExchange',
    'BitgetExchange',
    'OKXExchange',
    'BingXExchange',
    'UpbitExchange',
    'BithumbExchange',
]

def get_exchange_class(exchange_name: str):
    """거래소 이름으로 클래스 반환 (lazy import)"""
    exchange_name = exchange_name.lower()
    
    if exchange_name == 'bybit':
        from .bybit_exchange import BybitExchange
        return BybitExchange
    elif exchange_name == 'binance':
        from .binance_exchange import BinanceExchange
        return BinanceExchange
    elif exchange_name == 'lighter':
        from .lighter_exchange import LighterExchange
        return LighterExchange
    elif exchange_name == 'bitget':
        from .bitget_exchange import BitgetExchange
        return BitgetExchange
    elif exchange_name == 'okx':
        from .okx_exchange import OKXExchange
        return OKXExchange
    elif exchange_name == 'bingx':
        from .bingx_exchange import BingXExchange
        return BingXExchange
    elif exchange_name == 'upbit':
        from .upbit_exchange import UpbitExchange
        return UpbitExchange
    elif exchange_name == 'bithumb':
        from .bithumb_exchange import BithumbExchange
        return BithumbExchange
    else:
        # CCXT 범용 어댑터 사용
        from .ccxt_exchange import CCXTExchange
        return CCXTExchange

