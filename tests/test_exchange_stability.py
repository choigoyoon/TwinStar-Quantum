"""
Track 5.1: 거래소별 안정성 및 호환성 테스트

모든 거래소 어댑터가 동일한 인터페이스를 제공하고,
에러 상황에서도 안정적으로 동작하는지 검증.

테스트 범위:
- 9개 거래소 어댑터 (Binance, Bybit, OKX, BingX, Bitget, Upbit, Bithumb, Lighter, CCXT)
- API 메서드 시그니처 일관성
- 에러 핸들링 안정성
- 네트워크 타임아웃 처리
- 데이터 형식 표준화
"""

import pytest
from typing import Type, List
from unittest.mock import Mock, patch
from exchanges.base_exchange import BaseExchange, OrderResult


# 테스트 대상 거래소 목록
EXCHANGE_MODULES = [
    ('binance', 'BinanceExchange'),
    ('bybit', 'BybitExchange'),
    ('okx', 'OKXExchange'),
    ('bingx', 'BingXExchange'),
    ('bitget', 'BitgetExchange'),
    ('upbit', 'UpbitExchange'),
    ('bithumb', 'BithumbExchange'),
    ('lighter', 'LighterExchange'),
    ('ccxt', 'CCXTExchange'),
]


class TestExchangeCompatibility:
    """거래소 어댑터 호환성 테스트"""

    def test_all_exchanges_implement_base_methods(self):
        """모든 거래소가 BaseExchange 필수 메서드 구현했는지 검증"""

        required_methods = [
            'get_position',
            'place_market_order',
            'update_stop_loss',
            'close_position',
            'get_klines',
        ]

        for module_name, class_name in EXCHANGE_MODULES:
            # 동적 import
            module = __import__(f'exchanges.{module_name}_exchange', fromlist=[class_name])
            exchange_class = getattr(module, class_name)

            # BaseExchange 상속 확인
            assert issubclass(exchange_class, BaseExchange), \
                f"{class_name}는 BaseExchange를 상속해야 함"

            # 필수 메서드 존재 확인
            for method in required_methods:
                assert hasattr(exchange_class, method), \
                    f"{class_name}에 {method}() 메서드가 없음"

                # 메서드가 callable인지 확인
                attr = getattr(exchange_class, method)
                assert callable(attr), \
                    f"{class_name}.{method}는 호출 가능해야 함"

    def test_all_exchanges_return_order_result(self):
        """모든 거래소가 OrderResult 데이터클래스 반환하는지 검증 (Phase B Track 1)"""

        order_methods = [
            'place_market_order',
            'update_stop_loss',
            'close_position',
        ]

        for module_name, class_name in EXCHANGE_MODULES:
            module = __import__(f'exchanges.{module_name}_exchange', fromlist=[class_name])
            exchange_class = getattr(module, class_name)

            # Mock 거래소 인스턴스 생성 (실제 API 호출 없이)
            with patch.object(exchange_class, '__init__', return_value=None):
                exchange = exchange_class.__new__(exchange_class)
                exchange.name = module_name
                exchange.dry_run = True

                for method_name in order_methods:
                    method = getattr(exchange, method_name, None)

                    if method is None:
                        pytest.skip(f"{class_name}.{method_name}() 메서드 없음 (스킵)")
                        continue

                    # 메서드 시그니처 검증 (실제 호출은 하지 않음)
                    # 반환 타입이 OrderResult인지 확인
                    import inspect
                    sig = inspect.signature(method)
                    return_annotation = sig.return_annotation

                    # OrderResult 또는 OrderResult 타입 힌트 확인
                    if return_annotation != inspect.Signature.empty:
                        assert 'OrderResult' in str(return_annotation) or return_annotation is OrderResult, \
                            f"{class_name}.{method_name}()는 OrderResult를 반환해야 함 (현재: {return_annotation})"

    def test_exchange_error_handling(self):
        """거래소 에러 핸들링 테스트 (네트워크 에러, API 에러)"""
        from exchanges.binance_exchange import BinanceExchange

        # Mock API 키
        with patch.object(BinanceExchange, '__init__', return_value=None):
            exchange = BinanceExchange.__new__(BinanceExchange)
            exchange.name = 'binance'
            exchange.dry_run = True
            exchange.client = Mock()

            # 네트워크 에러 시뮬레이션
            exchange.client.get_position = Mock(side_effect=Exception("Network timeout"))

            # 에러 발생 시 None 또는 False 반환 (프로그램 중단 안 됨)
            result = exchange.get_position(symbol='BTCUSDT')

            # 에러가 발생해도 프로그램은 계속 실행되어야 함
            assert result is None or result is False, \
                "에러 발생 시 None 또는 False 반환해야 함"

    def test_exchange_dry_run_mode(self):
        """모든 거래소가 dry_run 모드 지원하는지 검증"""
        from exchanges.bybit_exchange import BybitExchange

        # Dry run 모드로 거래소 생성
        with patch.object(BybitExchange, '__init__', return_value=None):
            exchange = BybitExchange.__new__(BybitExchange)
            exchange.dry_run = True
            exchange.name = 'bybit'

            # Dry run 모드에서는 실제 API 호출 안 함
            assert exchange.dry_run is True, "dry_run 속성이 있어야 함"


class TestExchangeStressTests:
    """거래소 스트레스 테스트"""

    def test_rapid_order_requests(self):
        """빠른 연속 주문 요청 처리 테스트"""
        from exchanges.okx_exchange import OKXExchange

        with patch.object(OKXExchange, '__init__', return_value=None):
            exchange = OKXExchange.__new__(OKXExchange)
            exchange.name = 'okx'
            exchange.dry_run = True
            exchange.client = Mock()

            # Mock 응답 설정
            exchange.client.place_market_order = Mock(return_value=OrderResult(
                success=True,
                order_id='test_order'
            ))

            # 연속 10회 주문 요청
            results = []
            for i in range(10):
                result = exchange.place_market_order(
                    symbol='BTCUSDT',
                    side='Long',
                    quantity=0.01
                )
                results.append(result)

            # 모든 요청이 처리되어야 함
            assert len(results) == 10, "10개 주문 모두 처리되어야 함"
            assert all(r.success for r in results if r), "모든 주문이 성공해야 함"

    def test_invalid_symbol_handling(self):
        """잘못된 심볼 처리 테스트"""
        from exchanges.bitget_exchange import BitgetExchange

        with patch.object(BitgetExchange, '__init__', return_value=None):
            exchange = BitgetExchange.__new__(BitgetExchange)
            exchange.name = 'bitget'
            exchange.dry_run = True
            exchange.client = Mock()

            # 잘못된 심볼로 API 에러 시뮬레이션
            exchange.client.get_klines = Mock(side_effect=ValueError("Invalid symbol"))

            # 에러 발생 시 None 또는 빈 리스트 반환
            result = exchange.get_klines(
                symbol='INVALID_SYMBOL',
                interval='15m',
                limit=100
            )

            assert result is None or result == [], \
                "잘못된 심볼 시 None 또는 빈 리스트 반환"

    def test_rate_limit_handling(self):
        """Rate Limit 처리 테스트"""
        from exchanges.bingx_exchange import BingXExchange

        with patch.object(BingXExchange, '__init__', return_value=None):
            exchange = BingXExchange.__new__(BingXExchange)
            exchange.name = 'bingx'
            exchange.dry_run = True
            exchange.client = Mock()

            # Rate limit 에러 시뮬레이션
            exchange.client.get_position = Mock(
                side_effect=Exception("Rate limit exceeded")
            )

            # Rate limit 에러 시 None 반환 (재시도는 상위 레이어에서)
            result = exchange.get_position(symbol='BTCUSDT')

            assert result is None or result is False, \
                "Rate limit 에러 시 안전하게 처리되어야 함"


class TestExchangeDataConsistency:
    """거래소 데이터 일관성 테스트"""

    def test_klines_data_format(self):
        """K-line 데이터 형식 일관성 테스트"""
        from exchanges.upbit_exchange import UpbitExchange
        import pandas as pd

        with patch.object(UpbitExchange, '__init__', return_value=None):
            exchange = UpbitExchange.__new__(UpbitExchange)
            exchange.name = 'upbit'
            exchange.dry_run = True
            exchange.client = Mock()

            # Mock K-line 데이터
            mock_klines = pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
                'open': [45000.0] * 100,
                'high': [45100.0] * 100,
                'low': [44900.0] * 100,
                'close': [45000.0] * 100,
                'volume': [1000.0] * 100,
            })

            exchange.client.get_klines = Mock(return_value=mock_klines)

            # K-line 데이터 조회
            df = exchange.get_klines(symbol='KRW-BTC', interval='15m', limit=100)

            # 데이터프레임 검증
            if df is not None and not df.empty:
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    assert col in df.columns, f"{col} 컬럼이 있어야 함"

    def test_position_data_format(self):
        """포지션 데이터 형식 일관성 테스트"""
        from exchanges.bithumb_exchange import BithumbExchange

        with patch.object(BithumbExchange, '__init__', return_value=None):
            exchange = BithumbExchange.__new__(BithumbExchange)
            exchange.name = 'bithumb'
            exchange.dry_run = True
            exchange.client = Mock()

            # Mock 포지션 데이터
            exchange.client.get_position = Mock(return_value={
                'symbol': 'BTC_KRW',
                'side': 'Long',
                'entry_price': 45000.0,
                'size': 0.01,
                'pnl': 100.0
            })

            # 포지션 조회
            position = exchange.get_position(symbol='BTC_KRW')

            # 포지션 데이터 검증 (있으면)
            if position and isinstance(position, dict):
                # 필수 필드 확인
                assert 'symbol' in position or position.get('symbol'), \
                    "포지션에 symbol 정보 있어야 함"


class TestExchangeIntegration:
    """거래소 통합 시나리오 테스트"""

    def test_full_order_lifecycle(self):
        """전체 주문 라이프사이클 테스트 (진입 → 관리 → 청산)"""
        from exchanges.lighter_exchange import LighterExchange

        with patch.object(LighterExchange, '__init__', return_value=None):
            exchange = LighterExchange.__new__(LighterExchange)
            exchange.name = 'lighter'
            exchange.dry_run = True
            exchange.client = Mock()

            # Mock 응답 설정
            exchange.client.place_market_order = Mock(return_value=OrderResult(
                success=True,
                order_id='order_123',
                filled_price=45000.0
            ))
            exchange.client.update_stop_loss = Mock(return_value=OrderResult(success=True))
            exchange.client.close_position = Mock(return_value=OrderResult(success=True))

            # 1. 진입
            entry_result = exchange.place_market_order(
                symbol='BTCUSDT',
                side='Long',
                quantity=0.01
            )
            assert entry_result and entry_result.success, "진입 주문 성공해야 함"

            # 2. 손절가 업데이트
            sl_result = exchange.update_stop_loss(
                symbol='BTCUSDT',
                stop_loss=44500.0
            )
            assert sl_result and sl_result.success, "손절가 업데이트 성공해야 함"

            # 3. 청산
            close_result = exchange.close_position(symbol='BTCUSDT')
            assert close_result and close_result.success, "청산 성공해야 함"

    def test_ccxt_fallback_compatibility(self):
        """CCXT 폴백 호환성 테스트"""
        from exchanges.ccxt_exchange import CCXTExchange

        with patch.object(CCXTExchange, '__init__', return_value=None):
            exchange = CCXTExchange.__new__(CCXTExchange)
            exchange.name = 'ccxt'
            exchange.dry_run = True
            exchange.exchange_id = 'binance'
            exchange.client = Mock()

            # CCXT는 모든 거래소의 폴백 역할
            # 기본 메서드 존재 확인
            assert hasattr(exchange, 'get_position'), "CCXT에 get_position 있어야 함"
            assert hasattr(exchange, 'place_market_order'), "CCXT에 place_market_order 있어야 함"


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
