"""
WebSocket Symbol Normalization Manual Test
심볼 정규화 수동 테스트
"""

import sys
sys.path.insert(0, 'f:\\TwinStar-Quantum')

from exchanges.ws_handler import WebSocketHandler


def test_all_exchanges():
    """모든 거래소 심볼 정규화 테스트"""

    print("=" * 80)
    print("WebSocket Symbol Normalization Test")
    print("=" * 80)

    test_cases = [
        # (거래소, 입력 심볼, 예상 출력)
        ('bybit', 'BTCUSDT', 'BTCUSDT'),
        ('bybit', 'BTC/USDT', 'BTCUSDT'),
        ('bybit', 'btc-usdt', 'BTCUSDT'),

        ('binance', 'BTCUSDT', 'btcusdt'),
        ('binance', 'BTC/USDT', 'btcusdt'),
        ('binance', 'BTC-USDT', 'btcusdt'),

        ('upbit', 'KRW-BTC', 'KRW-BTC'),
        ('upbit', 'krw-btc', 'KRW-BTC'),

        ('bithumb', 'BTC-KRW', 'BTC_KRW'),
        ('bithumb', 'BTC/KRW', 'BTC_KRW'),

        ('okx', 'BTCUSDT', 'BTC-USDT-SWAP'),
        ('okx', 'BTC-USDT', 'BTC-USDT-SWAP'),

        ('bitget', 'BTCUSDT', 'BTCUSDT'),
        ('bitget', 'btcusdt', 'BTCUSDT'),

        ('bingx', 'BTCUSDT', 'BTC-USDT'),
        ('bingx', 'BTC-USDT', 'BTC-USDT'),
    ]

    passed = 0
    failed = 0

    for exchange, input_symbol, expected in test_cases:
        ws = WebSocketHandler(exchange, input_symbol, '15m')
        result = ws._normalize_symbol(exchange)

        if result == expected:
            print(f"✅ {exchange:10s} | {input_symbol:15s} → {result:20s} (OK)")
            passed += 1
        else:
            print(f"❌ {exchange:10s} | {input_symbol:15s} → {result:20s} (Expected: {expected})")
            failed += 1

    print("=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 80)

    # 구독 메시지 샘플 출력
    print("\n" + "=" * 80)
    print("Sample Subscribe Messages")
    print("=" * 80)

    sample_exchanges = [
        ('bybit', 'BTCUSDT'),
        ('binance', 'BTCUSDT'),
        ('upbit', 'KRW-BTC'),
        ('bithumb', 'BTC-KRW'),
        ('okx', 'BTCUSDT'),
        ('bingx', 'BTCUSDT'),
    ]

    for exchange, symbol in sample_exchanges:
        ws = WebSocketHandler(exchange, symbol, '15m')
        msg = ws.get_subscribe_message()
        print(f"\n{exchange.upper()}:")
        print(f"  Input: {symbol}")
        print(f"  Normalized: {ws._normalize_symbol(exchange)}")
        print(f"  Message: {msg}")

    print("=" * 80)

    return failed == 0


if __name__ == '__main__':
    success = test_all_exchanges()
    sys.exit(0 if success else 1)
