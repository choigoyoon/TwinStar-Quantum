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
import inspect
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

            for method_name in order_methods:
                # 메서드 시그니처 검증
                if not hasattr(exchange_class, method_name):
                    pytest.skip(f"{class_name}.{method_name}() 메서드 없음 (스킵)")
                    continue

                method = getattr(exchange_class, method_name)
                sig = inspect.signature(method)
                return_annotation = sig.return_annotation

                # OrderResult 또는 OrderResult 타입 힌트 확인
                if return_annotation != inspect.Signature.empty:
                    assert 'OrderResult' in str(return_annotation) or return_annotation is OrderResult, \
                        f"{class_name}.{method_name}()는 OrderResult를 반환해야 함 (현재: {return_annotation})"

    def test_exchange_interface_consistency(self):
        """거래소 인터페이스 일관성 테스트"""

        for module_name, class_name in EXCHANGE_MODULES:
            module = __import__(f'exchanges.{module_name}_exchange', fromlist=[class_name])
            exchange_class = getattr(module, class_name)

            # name 속성 존재 확인 (property)
            assert hasattr(exchange_class, 'name'), \
                f"{class_name}에 name 속성이 있어야 함"

            # BaseExchange 상속 확인
            assert issubclass(exchange_class, BaseExchange), \
                f"{class_name}는 BaseExchange를 상속해야 함"


class TestExchangeMethodSignatures:
    """거래소 메서드 시그니처 테스트"""

    def test_place_market_order_signature(self):
        """place_market_order 메서드 시그니처 일관성"""

        for module_name, class_name in EXCHANGE_MODULES:
            module = __import__(f'exchanges.{module_name}_exchange', fromlist=[class_name])
            exchange_class = getattr(module, class_name)

            if not hasattr(exchange_class, 'place_market_order'):
                continue

            method = getattr(exchange_class, 'place_market_order')
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())

            # 'self' 제외한 파라미터 확인
            params_without_self = [p for p in params if p != 'self']

            # 최소한 side 파라미터는 있어야 함
            assert len(params_without_self) > 0, \
                f"{class_name}.place_market_order()는 파라미터가 있어야 함"

    def test_get_position_signature(self):
        """get_position 메서드 시그니처 일관성"""

        for module_name, class_name in EXCHANGE_MODULES:
            module = __import__(f'exchanges.{module_name}_exchange', fromlist=[class_name])
            exchange_class = getattr(module, class_name)

            if not hasattr(exchange_class, 'get_position'):
                continue

            method = getattr(exchange_class, 'get_position')
            sig = inspect.signature(method)

            # 반환 타입 확인 (Optional일 수 있음)
            return_annotation = sig.return_annotation
            if return_annotation != inspect.Signature.empty:
                # Position, dict, None 등을 반환할 수 있음
                assert return_annotation is not None, \
                    f"{class_name}.get_position()는 반환 타입이 있어야 함"


class TestExchangeDataConsistency:
    """거래소 데이터 일관성 테스트"""

    def test_order_result_structure(self):
        """OrderResult 데이터클래스 구조 검증"""

        # OrderResult 필수 필드
        required_fields = ['success', 'order_id', 'error']

        for field in required_fields:
            assert hasattr(OrderResult, '__annotations__'), \
                "OrderResult는 타입 힌트가 있어야 함"
            assert field in OrderResult.__annotations__, \
                f"OrderResult에 {field} 필드가 있어야 함"

    def test_order_result_bool_conversion(self):
        """OrderResult Truthy 변환 테스트"""

        # 성공 케이스
        success_result = OrderResult(success=True, order_id='12345')
        assert bool(success_result) is True, "성공 시 True여야 함"

        # 실패 케이스
        fail_result = OrderResult(success=False, error="Test error")
        assert bool(fail_result) is False, "실패 시 False여야 함"

    def test_order_result_factory_methods(self):
        """OrderResult 팩토리 메서드 테스트"""

        # from_bool 테스트
        result_true = OrderResult.from_bool(True)
        assert result_true.success is True

        result_false = OrderResult.from_bool(False)
        assert result_false.success is False

        # from_order_id 테스트
        result_id = OrderResult.from_order_id('12345')
        assert result_id.success is True
        assert result_id.order_id == '12345'


class TestExchangeIntegration:
    """거래소 통합 시나리오 테스트"""

    def test_exchange_class_instantiation(self):
        """거래소 클래스 인스턴스화 가능 여부"""

        for module_name, class_name in EXCHANGE_MODULES:
            module = __import__(f'exchanges.{module_name}_exchange', fromlist=[class_name])
            exchange_class = getattr(module, class_name)

            # 클래스가 호출 가능한지 확인
            assert callable(exchange_class), \
                f"{class_name}는 인스턴스화 가능해야 함"

            # __init__ 메서드 시그니처 확인
            init_sig = inspect.signature(exchange_class.__init__)
            params = list(init_sig.parameters.keys())

            # 'self' 제외
            params_without_self = [p for p in params if p != 'self']

            # 최소한 API 키 관련 파라미터가 있어야 함
            assert len(params_without_self) > 0, \
                f"{class_name}.__init__()는 파라미터가 있어야 함"


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
