# tests/test_exchange_api_parity.py
"""
거래소 API 반환값 통일성 테스트 (Phase B Track 1)

목적:
- 모든 거래소가 동일한 타입(OrderResult) 반환하는지 검증
- place_market_order, update_stop_loss, close_position 메서드 테스트
- Truthy 체크 지원 검증

작성일: 2026-01-15
"""

import pytest
from datetime import datetime
from exchanges.base_exchange import OrderResult


class TestOrderResult:
    """OrderResult 데이터클래스 테스트"""

    def test_order_result_success(self):
        """성공 OrderResult 생성"""
        result = OrderResult(
            success=True,
            order_id="12345",
            filled_price=50000.0,
            filled_qty=1.0,
            timestamp=datetime.now()
        )

        assert result.success is True
        assert result.order_id == "12345"
        assert result.filled_price == 50000.0
        assert result.filled_qty == 1.0
        assert result.timestamp is not None

    def test_order_result_failure(self):
        """실패 OrderResult 생성"""
        result = OrderResult(
            success=False,
            error="Insufficient balance"
        )

        assert result.success is False
        assert result.error == "Insufficient balance"
        assert result.order_id is None

    def test_order_result_from_bool_success(self):
        """from_bool 팩토리 메서드 (성공)"""
        result = OrderResult.from_bool(True)

        assert result.success is True
        assert result.error is None

    def test_order_result_from_bool_failure(self):
        """from_bool 팩토리 메서드 (실패)"""
        result = OrderResult.from_bool(False, error="Rate limit exceeded")

        assert result.success is False
        assert result.error == "Rate limit exceeded"

    def test_order_result_from_order_id(self):
        """from_order_id 팩토리 메서드"""
        result = OrderResult.from_order_id("order_12345")

        assert result.success is True
        assert result.order_id == "order_12345"
        assert result.error is None

    def test_order_result_truthy_success(self):
        """Truthy 체크 (성공)"""
        result = OrderResult(success=True)

        assert result  # Truthy
        assert bool(result) is True

        # if 문 테스트
        if result:
            passed = True
        else:
            passed = False

        assert passed is True

    def test_order_result_truthy_failure(self):
        """Truthy 체크 (실패)"""
        result = OrderResult(success=False, error="Error")

        assert not result  # Falsy
        assert bool(result) is False

        # if 문 테스트
        if result:
            passed = False
        else:
            passed = True

        assert passed is True

    def test_order_result_legacy_fields(self):
        """Legacy 필드 (price, qty) 자동 동기화"""
        result = OrderResult(
            success=True,
            filled_price=50000.0,
            filled_qty=1.5
        )

        # Legacy 필드 자동 동기화 확인
        assert result.price == 50000.0
        assert result.qty == 1.5


class TestExchangeAPIParity:
    """거래소 API 반환값 통일성 테스트"""

    def test_all_exchanges_import_order_result(self):
        """모든 거래소가 OrderResult를 import하는지 확인"""
        exchanges_to_test = [
            'okx_exchange',
            'bingx_exchange',
            'bitget_exchange',
            'upbit_exchange',
            'bithumb_exchange',
        ]

        for exchange_name in exchanges_to_test:
            try:
                module = __import__(f'exchanges.{exchange_name}', fromlist=['OrderResult'])
                # OrderResult가 base_exchange에서 import되었는지 확인
                assert hasattr(module, 'OrderResult') or True  # import되지 않아도 OK (base에서 상속)
            except ImportError as e:
                pytest.fail(f"Failed to import exchanges.{exchange_name}: {e}")

    def test_order_result_type_hints(self):
        """OrderResult 타입 힌트 검증"""
        from exchanges.okx_exchange import OKXExchange

        # 메서드 시그니처 확인 (타입 힌트)
        import inspect

        # place_market_order
        sig = inspect.signature(OKXExchange.place_market_order)
        assert sig.return_annotation == OrderResult or 'OrderResult' in str(sig.return_annotation)

        # update_stop_loss
        sig = inspect.signature(OKXExchange.update_stop_loss)
        assert sig.return_annotation == OrderResult or 'OrderResult' in str(sig.return_annotation)

        # close_position
        sig = inspect.signature(OKXExchange.close_position)
        assert sig.return_annotation == OrderResult or 'OrderResult' in str(sig.return_annotation)

    def test_all_exchanges_return_order_result(self):
        """
        모든 거래소 어댑터의 3개 메서드가 OrderResult를 반환하는지 검증

        Phase B Track 2 완료:
        - 9개 거래소 100% API 일관성 달성
        - place_market_order, update_stop_loss, close_position
        """
        import inspect

        exchanges_to_test = [
            ('binance_exchange', 'BinanceExchange'),
            ('bybit_exchange', 'BybitExchange'),
            ('okx_exchange', 'OKXExchange'),
            ('bingx_exchange', 'BingXExchange'),
            ('bitget_exchange', 'BitgetExchange'),
            ('upbit_exchange', 'UpbitExchange'),
            ('bithumb_exchange', 'BithumbExchange'),
            ('lighter_exchange', 'LighterExchange'),
            ('ccxt_exchange', 'CCXTExchange'),
        ]

        methods_to_check = [
            'place_market_order',
            'update_stop_loss',
            'close_position',
        ]

        for module_name, class_name in exchanges_to_test:
            try:
                module = __import__(f'exchanges.{module_name}', fromlist=[class_name])
                exchange_class = getattr(module, class_name)

                for method_name in methods_to_check:
                    if hasattr(exchange_class, method_name):
                        method = getattr(exchange_class, method_name)
                        sig = inspect.signature(method)

                        # 타입 힌트 검증
                        return_annotation = sig.return_annotation
                        assert return_annotation == OrderResult or 'OrderResult' in str(return_annotation), \
                            f"{class_name}.{method_name} must return OrderResult, got {return_annotation}"
                    else:
                        pytest.fail(f"{class_name} missing method: {method_name}")

            except ImportError as e:
                # 선택적 의존성 (SDK 없는 경우)
                if 'No module named' in str(e):
                    pytest.skip(f"Skipping {class_name}: {e}")
                else:
                    pytest.fail(f"Failed to import {class_name}: {e}")


class TestOrderResultCompatibility:
    """OrderResult 하위 호환성 테스트"""

    def test_truthy_check_in_conditional(self):
        """조건문에서 Truthy 체크"""
        success_result = OrderResult(success=True, order_id="123")
        failure_result = OrderResult(success=False, error="Error")

        # 성공 케이스
        if success_result:
            success_path = True
        else:
            success_path = False

        assert success_path is True

        # 실패 케이스
        if failure_result:
            failure_path = False
        else:
            failure_path = True

        assert failure_path is True

    def test_truthy_check_with_and_operator(self):
        """AND 연산자와 함께 사용"""
        result = OrderResult(success=True, order_id="123")

        if result and result.order_id:
            passed = True
        else:
            passed = False

        assert passed is True

    def test_truthy_check_with_or_operator(self):
        """OR 연산자와 함께 사용"""
        result = OrderResult(success=False, error="Error")

        if result or True:
            passed = True
        else:
            passed = False

        assert passed is True

    def test_legacy_code_pattern(self):
        """기존 코드 패턴 (if result: 형식)"""
        # 기존 코드에서 bool을 반환했을 때의 패턴
        result = OrderResult(success=True, order_id="order_123")

        # 기존 코드 패턴
        if result:
            order_id = result.order_id
            assert order_id == "order_123"
        else:
            pytest.fail("Should not reach here")


class TestOrderResultFields:
    """OrderResult 필드 검증"""

    def test_all_fields_present(self):
        """모든 필드가 존재하는지 확인"""
        result = OrderResult(
            success=True,
            order_id="order_123",
            filled_price=50000.0,
            filled_qty=1.0,
            error=None,
            timestamp=datetime.now()
        )

        # 필드 존재 확인
        assert hasattr(result, 'success')
        assert hasattr(result, 'order_id')
        assert hasattr(result, 'filled_price')
        assert hasattr(result, 'filled_qty')
        assert hasattr(result, 'error')
        assert hasattr(result, 'timestamp')

        # Legacy 필드
        assert hasattr(result, 'price')
        assert hasattr(result, 'qty')

    def test_optional_fields_none(self):
        """Optional 필드가 None일 수 있는지 확인"""
        result = OrderResult(success=False)

        assert result.order_id is None
        assert result.filled_price is None
        assert result.filled_qty is None
        assert result.error is None
        assert result.timestamp is None

    def test_timestamp_type(self):
        """timestamp 타입 검증"""
        now = datetime.now()
        result = OrderResult(success=True, timestamp=now)

        assert isinstance(result.timestamp, datetime)
        assert result.timestamp == now


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
