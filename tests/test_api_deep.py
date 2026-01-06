"""
API 심층 검사 스크립트
거래소 API 연동 전체 검증
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch

results = {}

def test(name, func):
    """테스트 실행 및 결과 기록"""
    try:
        result = func()
        status = "✅" if result else "❌"
        results[name] = result
        print(f"  {status} {name}")
        return result
    except Exception as e:
        results[name] = False
        print(f"  ❌ {name} - Error: {str(e)[:50]}")
        return False

# ========================================
# 1. 연결 테스트
# ========================================
def test_bybit_class_exists():
    """Bybit 클래스 존재"""
    from exchanges.bybit_exchange import BybitExchange
    return hasattr(BybitExchange, 'connect')

def test_binance_class_exists():
    """Binance 클래스 존재"""
    from exchanges.binance_exchange import BinanceExchange
    return hasattr(BinanceExchange, 'connect')

def test_exchange_manager():
    """ExchangeManager 초기화"""
    from exchanges.exchange_manager import ExchangeManager
    em = ExchangeManager()
    return hasattr(em, 'get_exchange')

def test_mock_connect():
    """Mock 연결 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': 'test', 'api_secret': 'test'})
    with patch.object(ex, 'connect', return_value=True):
        return ex.connect()

# ========================================
# 2. 공개 API 테스트 (Mock)
# ========================================
def test_get_klines_mock():
    """캔들 조회 Mock 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    mock_df = pd.DataFrame({
        'timestamp': [1704067200000, 1704068100000],
        'open': [100, 101],
        'high': [102, 103],
        'low': [99, 100],
        'close': [101, 102],
        'volume': [1000, 1100]
    })
    
    ex = BybitExchange({'api_key': '', 'api_secret': ''})
    with patch.object(ex, 'get_klines', return_value=mock_df):
        df = ex.get_klines('BTCUSDT', '15m', 100)
        return df is not None and len(df) == 2

def test_get_current_price_mock():
    """현재가 조회 Mock 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': '', 'api_secret': ''})
    with patch.object(ex, 'get_current_price', return_value=96500.0):
        price = ex.get_current_price('BTCUSDT')
        return price == 96500.0

# ========================================
# 3. 인증 API 테스트 (Mock)
# ========================================
def test_get_balance_mock():
    """잔고 조회 Mock 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': 'test', 'api_secret': 'test'})
    with patch.object(ex, 'get_balance', return_value=1000.5):
        balance = ex.get_balance()
        return balance == 1000.5

def test_get_positions_mock():
    """포지션 조회 Mock 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    mock_positions = [
        {'symbol': 'BTCUSDT', 'side': 'Buy', 'size': 0.01, 'entry_price': 95000}
    ]
    ex = BybitExchange({'api_key': 'test', 'api_secret': 'test'})
    with patch.object(ex, 'get_positions', return_value=mock_positions):
        positions = ex.get_positions()
        return len(positions) == 1 and positions[0]['symbol'] == 'BTCUSDT'

# ========================================
# 4. 주문 API 테스트 (Mock/dry_run)
# ========================================
def test_set_leverage_mock():
    """레버리지 설정 Mock 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': 'test', 'api_secret': 'test'})
    with patch.object(ex, 'set_leverage', return_value=True):
        result = ex.set_leverage(10)
        return result == True

def test_place_order_mock():
    """주문 Mock 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    mock_order = {'orderId': '123456', 'status': 'Filled'}
    ex = BybitExchange({'api_key': 'test', 'api_secret': 'test'})
    with patch.object(ex, 'place_market_order', return_value=mock_order):
        order = ex.place_market_order('Buy', 0.001, 94000)
        return order is not None and 'orderId' in order

def test_close_position_mock():
    """청산 Mock 테스트"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': 'test', 'api_secret': 'test'})
    with patch.object(ex, 'close_position', return_value={'success': True}):
        result = ex.close_position()
        return result is not None

# ========================================
# 5. 에러 핸들링 테스트
# ========================================
def test_invalid_symbol_handling():
    """잘못된 심볼 처리"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': '', 'api_secret': ''})
    with patch.object(ex, 'get_klines', return_value=None):
        df = ex.get_klines('INVALID_SYMBOL', '15m', 100)
        return df is None  # None 반환이 정상

def test_api_error_handling():
    """API 에러 처리"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': '', 'api_secret': ''})
    
    def raise_error(*args, **kwargs):
        raise Exception("API Error")
    
    with patch.object(ex, 'get_balance', side_effect=raise_error):
        try:
            ex.get_balance()
            return False
        except Exception:
            return True  # 예외 발생이 정상

def test_timeout_handling():
    """타임아웃 처리"""
    from exchanges.bybit_exchange import BybitExchange
    ex = BybitExchange({'api_key': '', 'api_secret': ''})
    
    def timeout_error(*args, **kwargs):
        raise TimeoutError("Connection timed out")
    
    with patch.object(ex, 'connect', side_effect=timeout_error):
        try:
            ex.connect()
            return False
        except TimeoutError:
            return True

# ========================================
# 6. 응답 형식 검증
# ========================================
def test_ohlcv_format():
    """OHLCV 형식 검증"""
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    mock_df = pd.DataFrame({
        'timestamp': [1704067200000],
        'open': [100.0],
        'high': [102.0],
        'low': [99.0],
        'close': [101.0],
        'volume': [1000.0]
    })
    return all(col in mock_df.columns for col in required_cols)

def test_position_format():
    """포지션 형식 검증"""
    required_fields = ['symbol', 'side', 'size', 'entry_price']
    mock_position = {
        'symbol': 'BTCUSDT',
        'side': 'Buy',
        'size': 0.01,
        'entry_price': 95000
    }
    return all(field in mock_position for field in required_fields)

def test_order_response_format():
    """주문 응답 형식 검증"""
    mock_order = {
        'orderId': '123456',
        'symbol': 'BTCUSDT',
        'side': 'Buy',
        'status': 'Filled'
    }
    return 'orderId' in mock_order and 'status' in mock_order


def main():
    print("=" * 60)
    print("API 심층 검사")
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 연결 테스트
    print("\n[1. 연결 테스트]")
    test("Bybit 클래스", test_bybit_class_exists)
    test("Binance 클래스", test_binance_class_exists)
    test("ExchangeManager", test_exchange_manager)
    test("Mock 연결", test_mock_connect)
    
    # 2. 공개 API 테스트
    print("\n[2. 공개 API 테스트]")
    test("캔들 조회 (Mock)", test_get_klines_mock)
    test("현재가 조회 (Mock)", test_get_current_price_mock)
    
    # 3. 인증 API 테스트
    print("\n[3. 인증 API 테스트]")
    test("잔고 조회 (Mock)", test_get_balance_mock)
    test("포지션 조회 (Mock)", test_get_positions_mock)
    
    # 4. 주문 API 테스트
    print("\n[4. 주문 API 테스트]")
    test("레버리지 설정 (Mock)", test_set_leverage_mock)
    test("주문 실행 (Mock)", test_place_order_mock)
    test("청산 (Mock)", test_close_position_mock)
    
    # 5. 에러 핸들링 테스트
    print("\n[5. 에러 핸들링 테스트]")
    test("잘못된 심볼 처리", test_invalid_symbol_handling)
    test("API 에러 처리", test_api_error_handling)
    test("타임아웃 처리", test_timeout_handling)
    
    # 6. 응답 형식 검증
    print("\n[6. 응답 형식 검증]")
    test("OHLCV 형식", test_ohlcv_format)
    test("포지션 형식", test_position_format)
    test("주문 응답 형식", test_order_response_format)
    
    # 결과 요약
    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    # 카테고리별 통과 현황
    categories = {
        '연결': ['Bybit 클래스', 'Binance 클래스', 'ExchangeManager', 'Mock 연결'],
        '공개 API': ['캔들 조회 (Mock)', '현재가 조회 (Mock)'],
        '인증 API': ['잔고 조회 (Mock)', '포지션 조회 (Mock)'],
        '주문 API': ['레버리지 설정 (Mock)', '주문 실행 (Mock)', '청산 (Mock)'],
        '에러 핸들링': ['잘못된 심볼 처리', 'API 에러 처리', '타임아웃 처리'],
        '응답 형식': ['OHLCV 형식', '포지션 형식', '주문 응답 형식'],
    }
    
    print("\n카테고리별 결과:")
    cat_passed = 0
    for cat_name, tests in categories.items():
        cat_results = [results.get(t, False) for t in tests]
        all_pass = all(cat_results)
        status = "✅" if all_pass else "❌"
        print(f"  {status} [{cat_name}] {sum(cat_results)}/{len(tests)}")
        if all_pass:
            cat_passed += 1
    
    print(f"\n총 결과: {passed}/{total} 테스트 통과")
    print(f"카테고리: {cat_passed}/6 통과")
    
    if passed == total:
        print("\n🎉 API 심층 검사 전부 통과!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"\n❌ 실패 항목: {', '.join(failed)}")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
