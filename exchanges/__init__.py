# exchanges/__init__.py
"""
거래소 어댑터 모듈
"""

from .base_exchange import BaseExchange, Position, Signal
from .bybit_exchange import BybitExchange
from .binance_exchange import BinanceExchange
from .lighter_exchange import LighterExchange
from .ccxt_exchange import CCXTExchange
from .bitget_exchange import BitgetExchange
from .okx_exchange import OKXExchange
from .bingx_exchange import BingXExchange
from .upbit_exchange import UpbitExchange
from .bithumb_exchange import BithumbExchange

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
    """거래소 이름으로 클래스 반환"""
    exchange_map = {
        'bybit': BybitExchange,
        'binance': BinanceExchange,
        'lighter': LighterExchange,
        'bitget': BitgetExchange,
        'okx': OKXExchange,
        'bingx': BingXExchange,
        'upbit': UpbitExchange,
        'bithumb': BithumbExchange,
    }

    exchange_name = exchange_name.lower()
    return exchange_map.get(exchange_name, CCXTExchange)

