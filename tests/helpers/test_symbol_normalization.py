"""
WebSocket Symbol Normalization Tests
거래소별 심볼 정규화 테스트
"""

import pytest
from exchanges.ws_handler import WebSocketHandler


class TestSymbolNormalization:
    """심볼 정규화 테스트"""

    def test_bybit_normalization(self):
        """Bybit: 대문자, 하이픈 제거"""
        ws = WebSocketHandler('bybit', 'BTC/USDT', '15m')
        assert ws._normalize_symbol('bybit') == 'BTCUSDT'

        ws = WebSocketHandler('bybit', 'btc-usdt', '15m')
        assert ws._normalize_symbol('bybit') == 'BTCUSDT'

        ws = WebSocketHandler('bybit', 'BTC_USDT', '15m')
        assert ws._normalize_symbol('bybit') == 'BTCUSDT'

    def test_binance_normalization(self):
        """Binance: 소문자, 하이픈 제거"""
        ws = WebSocketHandler('binance', 'BTCUSDT', '15m')
        assert ws._normalize_symbol('binance') == 'btcusdt'

        ws = WebSocketHandler('binance', 'BTC/USDT', '15m')
        assert ws._normalize_symbol('binance') == 'btcusdt'

        ws = WebSocketHandler('binance', 'BTC-USDT', '15m')
        assert ws._normalize_symbol('binance') == 'btcusdt'

    def test_upbit_normalization(self):
        """Upbit: 대문자, 하이픈 유지"""
        ws = WebSocketHandler('upbit', 'KRW-BTC', '15m')
        assert ws._normalize_symbol('upbit') == 'KRW-BTC'

        ws = WebSocketHandler('upbit', 'krw-btc', '15m')
        assert ws._normalize_symbol('upbit') == 'KRW-BTC'

    def test_bithumb_normalization(self):
        """Bithumb: 언더스코어 변환"""
        ws = WebSocketHandler('bithumb', 'BTC-KRW', '15m')
        assert ws._normalize_symbol('bithumb') == 'BTC_KRW'

        ws = WebSocketHandler('bithumb', 'BTC/KRW', '15m')
        assert ws._normalize_symbol('bithumb') == 'BTC_KRW'

        ws = WebSocketHandler('bithumb', 'btc-krw', '15m')
        assert ws._normalize_symbol('bithumb') == 'BTC_KRW'

    def test_okx_normalization(self):
        """OKX: 하이픈 + SWAP 접미사"""
        ws = WebSocketHandler('okx', 'BTCUSDT', '15m')
        assert ws._normalize_symbol('okx') == 'BTC-USDT-SWAP'

        ws = WebSocketHandler('okx', 'BTC-USDT', '15m')
        assert ws._normalize_symbol('okx') == 'BTC-USDT-SWAP'

        ws = WebSocketHandler('okx', 'BTC-USDT-SWAP', '15m')
        assert ws._normalize_symbol('okx') == 'BTC-USDT-SWAP'

    def test_bitget_normalization(self):
        """Bitget: 대문자 유지"""
        ws = WebSocketHandler('bitget', 'BTCUSDT', '15m')
        assert ws._normalize_symbol('bitget') == 'BTCUSDT'

        ws = WebSocketHandler('bitget', 'btcusdt', '15m')
        assert ws._normalize_symbol('bitget') == 'BTCUSDT'

    def test_bingx_normalization(self):
        """BingX: 하이픈 변환"""
        ws = WebSocketHandler('bingx', 'BTCUSDT', '15m')
        assert ws._normalize_symbol('bingx') == 'BTC-USDT'

        ws = WebSocketHandler('bingx', 'BTC-USDT', '15m')
        assert ws._normalize_symbol('bingx') == 'BTC-USDT'

        ws = WebSocketHandler('bingx', 'btcusdt', '15m')
        assert ws._normalize_symbol('bingx') == 'BTC-USDT'


class TestSubscribeMessage:
    """구독 메시지 생성 테스트"""

    def test_bybit_subscribe(self):
        """Bybit 구독 메시지"""
        ws = WebSocketHandler('bybit', 'BTC/USDT', '15m')
        msg = ws.get_subscribe_message()
        assert msg == {"op": "subscribe", "args": ["kline.15.BTCUSDT"]}

    def test_binance_subscribe(self):
        """Binance 구독 메시지"""
        ws = WebSocketHandler('binance', 'BTCUSDT', '15m')
        msg = ws.get_subscribe_message()
        assert isinstance(msg, dict)
        assert msg.get('method') == 'SUBSCRIBE'
        assert msg.get('params') == ['btcusdt@kline_15m']

    def test_upbit_subscribe(self):
        """Upbit 구독 메시지"""
        ws = WebSocketHandler('upbit', 'KRW-BTC', '15m')
        msg = ws.get_subscribe_message()
        assert isinstance(msg, list)
        assert msg[1]['codes'] == ['KRW-BTC']

    def test_bithumb_subscribe(self):
        """Bithumb 구독 메시지"""
        ws = WebSocketHandler('bithumb', 'BTC-KRW', '15m')
        msg = ws.get_subscribe_message()
        assert isinstance(msg, dict)
        assert msg.get('symbols') == ['BTC_KRW']

    def test_okx_subscribe(self):
        """OKX 구독 메시지"""
        ws = WebSocketHandler('okx', 'BTCUSDT', '15m')
        msg = ws.get_subscribe_message()
        assert isinstance(msg, dict)
        args = msg.get('args')
        assert isinstance(args, list) and len(args) > 0
        assert args[0].get('instId') == 'BTC-USDT-SWAP'

    def test_bingx_subscribe(self):
        """BingX 구독 메시지"""
        ws = WebSocketHandler('bingx', 'BTCUSDT', '15m')
        msg = ws.get_subscribe_message()
        assert isinstance(msg, dict)
        data_type = msg.get('dataType')
        assert isinstance(data_type, str)
        assert 'BTC-USDT@kline_15m' in data_type


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_whitespace_handling(self):
        """공백 처리"""
        ws = WebSocketHandler('bybit', ' BTCUSDT ', '15m')
        assert ws._normalize_symbol('bybit') == 'BTCUSDT'

    def test_mixed_case_handling(self):
        """대소문자 혼합 처리"""
        ws = WebSocketHandler('bybit', 'BtCuSdT', '15m')
        assert ws._normalize_symbol('bybit') == 'BTCUSDT'

    def test_multiple_separators(self):
        """다중 구분자 처리"""
        ws = WebSocketHandler('bybit', 'BTC-/USDT', '15m')
        assert ws._normalize_symbol('bybit') == 'BTCUSDT'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
