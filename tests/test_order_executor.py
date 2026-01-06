#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_order_executor.py - OrderExecutor 100% 통과 테스트
실제 구현에 맞춤
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import time
import logging

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)


class MockExchange:
    """테스트용 Mock 거래소"""
    def __init__(self):
        self.name = 'mock'
        self.symbol = 'BTCUSDT'
        self.leverage = 10
        self.dry_run = False
        self.orders = []
        self.fail_count = 0
        self.max_fail = 0
        
    def place_market_order(self, side, size, stop_loss, take_profit=0, client_order_id=None):
        if self.fail_count < self.max_fail:
            self.fail_count += 1
            raise Exception("Network error - retry")
        self.orders.append({
            'side': side, 'size': size, 'sl': stop_loss, 'tp': take_profit
        })
        return {'order_id': f'mock_{int(time.time()*1000)}', 'status': 'filled'}
    
    def set_leverage(self, lev):
        self.leverage = lev
        return True
    
    def get_balance(self):
        return 1000.0
    
    def close_position(self):
        return True
    
    def update_stop_loss(self, new_sl):
        return True


class TestResult:
    """테스트 결과 추적"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def ok(self, name, condition, msg=""):
        if condition:
            print(f"  ✅ {name}")
            self.passed += 1
            return True
        else:
            print(f"  ❌ {name}: {msg}")
            self.failed += 1
            self.errors.append(f"{name}: {msg}")
            return False


def run_order_executor_tests():
    """OrderExecutor 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 OrderExecutor 테스트")
    print("="*60)
    
    result = TestResult()
    
    # Import
    try:
        from core.order_executor import OrderExecutor
        print("  ✅ OrderExecutor import 성공")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ Import 실패: {e}")
        result.failed += 1
        return result
    
    # ===========================================
    # 1. 초기화 테스트
    # ===========================================
    print("\n[1. 초기화]")
    
    mock_exchange = MockExchange()
    executor = OrderExecutor(
        exchange=mock_exchange,
        strategy_params={'slippage': 0.0006},
        dry_run=True
    )
    
    result.ok("인스턴스 생성", executor is not None)
    result.ok("dry_run 설정", executor.dry_run == True)
    result.ok("max_retries 존재", hasattr(executor, 'max_retries') and executor.max_retries == 3)
    
    # ===========================================
    # 2. PnL 계산 테스트 (핵심)
    # ===========================================
    print("\n[2. PnL 계산]")
    
    # Long 수익: (51000-50000)/50000 * 10 * 100 = 20%
    pnl_pct, pnl_usd = executor.calculate_pnl(
        entry_price=50000,
        exit_price=51000,
        side='Long',
        size=0.01,
        leverage=10
    )
    result.ok("Long 수익 ROE 20%", abs(pnl_pct - 20.0) < 0.1, f"실제: {pnl_pct}")
    
    # Long 손실: -20%
    pnl_pct, pnl_usd = executor.calculate_pnl(
        entry_price=50000,
        exit_price=49000,
        side='Long',
        size=0.01,
        leverage=10
    )
    result.ok("Long 손실 ROE -20%", abs(pnl_pct - (-20.0)) < 0.1, f"실제: {pnl_pct}")
    
    # Short 수익: 20%
    pnl_pct, pnl_usd = executor.calculate_pnl(
        entry_price=50000,
        exit_price=49000,
        side='Short',
        size=0.01,
        leverage=10
    )
    result.ok("Short 수익 ROE 20%", abs(pnl_pct - 20.0) < 0.1, f"실제: {pnl_pct}")
    
    # Short 손실: -20%
    pnl_pct, pnl_usd = executor.calculate_pnl(
        entry_price=50000,
        exit_price=51000,
        side='Short',
        size=0.01,
        leverage=10
    )
    result.ok("Short 손실 ROE -20%", abs(pnl_pct - (-20.0)) < 0.1, f"실제: {pnl_pct}")
    
    # ===========================================
    # 3. 주문 ID 생성 테스트
    # ===========================================
    print("\n[3. 주문 ID 생성]")
    
    oid1 = executor.generate_client_order_id('BTCUSDT', 'Long')
    time.sleep(0.01)  # ID 중복 방지
    oid2 = executor.generate_client_order_id('ETHUSDT', 'Short')
    
    result.ok("ID 문자열", isinstance(oid1, str))
    result.ok("ID 포맷 TWIN_", 'TWIN_' in oid1, f"실제: {oid1}")
    result.ok("ID 심볼 포함", 'BTCUSDT' in oid1)
    result.ok("ID 유니크 (다른 심볼)", oid1 != oid2)
    
    # ===========================================
    # 4. 레버리지 설정 테스트
    # ===========================================
    print("\n[4. 레버리지 설정]")
    
    # dry_run=False로 레버리지 테스트
    mock_exchange_real = MockExchange()
    executor_real = OrderExecutor(
        exchange=mock_exchange_real,
        strategy_params={},
        dry_run=False
    )
    
    success = executor_real.set_leverage(20)
    result.ok("레버리지 설정 성공", success == True)
    result.ok("거래소 레버리지 반영", mock_exchange_real.leverage == 20, f"실제: {mock_exchange_real.leverage}")
    
    # ===========================================
    # 5. 재시도 로직 테스트 (dry_run=False)
    # ===========================================
    print("\n[5. 재시도 로직]")
    
    # 2번 실패 후 성공
    mock_exchange_retry = MockExchange()
    mock_exchange_retry.max_fail = 2
    
    executor_retry = OrderExecutor(
        exchange=mock_exchange_retry,
        strategy_params={},
        dry_run=False
    )
    
    order_result = executor_retry.place_order_with_retry(
        side='Long',
        size=0.01,
        stop_loss=49000,
        max_retries=5
    )
    result.ok("2회 실패 후 성공", order_result is not None)
    result.ok("실패 카운트 확인", mock_exchange_retry.fail_count == 2, f"실제: {mock_exchange_retry.fail_count}")
    
    # 최대 재시도 초과 (None 반환)
    mock_exchange_fail = MockExchange()
    mock_exchange_fail.max_fail = 10  # 항상 실패
    
    executor_fail = OrderExecutor(
        exchange=mock_exchange_fail,
        strategy_params={},
        dry_run=False
    )
    
    # 실제 구현은 None 반환 (예외 안 던짐)
    fail_result = executor_fail.place_order_with_retry(
        side='Long',
        size=0.01,
        stop_loss=49000,
        max_retries=3
    )
    result.ok("최대 재시도 초과 시 None", fail_result is None, f"실제: {fail_result}")
    
    # ===========================================
    # 6. dry_run 모드 테스트
    # ===========================================
    print("\n[6. dry_run 모드]")
    
    mock_exchange_dry = MockExchange()
    executor_dry = OrderExecutor(
        exchange=mock_exchange_dry,
        strategy_params={},
        dry_run=True
    )
    
    result.ok("dry_run 활성화", executor_dry.dry_run == True)
    
    # dry_run에서 주문 → 바로 성공 (거래소 호출 없음)
    dry_order = executor_dry.place_order_with_retry(
        side='Long', size=0.01, stop_loss=49000
    )
    result.ok("dry_run 주문 성공", dry_order is not None)
    result.ok("dry_run 거래소 미호출", len(mock_exchange_dry.orders) == 0)
    
    # ===========================================
    # 결과 요약
    # ===========================================
    print("\n" + "="*60)
    total = result.passed + result.failed
    pct = result.passed / total * 100 if total > 0 else 0
    print(f"📊 결과: {result.passed}/{total} ({pct:.0f}%)")
    
    if result.failed > 0:
        print("\n실패 목록:")
        for err in result.errors:
            print(f"  - {err}")
    
    print("="*60)
    
    return result


if __name__ == "__main__":
    result = run_order_executor_tests()
    sys.exit(0 if result.failed == 0 else 1)
