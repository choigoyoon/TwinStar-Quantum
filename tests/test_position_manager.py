#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_position_manager.py - PositionManager 100% 통과 테스트
"""
import sys
import os
from pathlib import Path
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
        self.sl_updates = []
        
    def update_stop_loss(self, new_sl):
        self.sl_updates.append(new_sl)
        return True
    
    def get_positions(self):
        return []
    
    def close_position(self):
        return True


class MockPosition:
    """테스트용 Mock 포지션"""
    def __init__(self, side='Long', entry_price=50000, stop_loss=49000, add_count=0):
        self.side = side
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.add_count = add_count
        self.size = 0.01


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


def run_position_manager_tests():
    """PositionManager 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 PositionManager 테스트")
    print("="*60)
    
    result = TestResult()
    
    # Import
    try:
        from core.position_manager import PositionManager
        print("  ✅ PositionManager import 성공")
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
    manager = PositionManager(
        exchange=mock_exchange,
        strategy_params={
            'trail_start_r': 0.8,
            'trail_dist_r': 0.5,
            'enable_pullback': True,
            'max_adds': 2,
            'pullback_rsi_long': 45,
            'pullback_rsi_short': 55
        },
        dry_run=True
    )
    
    result.ok("인스턴스 생성", manager is not None)
    result.ok("dry_run 설정", manager.dry_run == True)
    result.ok("strategy_params max_adds=2", manager.strategy_params.get('max_adds') == 2)
    
    # ===========================================
    # 2. SL 히트 감지 테스트
    # ===========================================
    print("\n[2. SL 히트 감지]")
    
    # Long 포지션 - SL 히트
    pos_long = MockPosition(side='Long', stop_loss=49000)
    sl_hit = manager.check_sl_hit(pos_long, high=50500, low=48900)
    result.ok("Long SL 히트 (low=48900 <= SL=49000)", sl_hit == True)
    
    # Long 포지션 - SL 미히트
    sl_no_hit = manager.check_sl_hit(pos_long, high=50500, low=49100)
    result.ok("Long SL 미히트 (low=49100 > SL=49000)", sl_no_hit == False)
    
    # Short 포지션 - SL 히트
    pos_short = MockPosition(side='Short', stop_loss=51000)
    sl_hit = manager.check_sl_hit(pos_short, high=51100, low=50500)
    result.ok("Short SL 히트 (high=51100 >= SL=51000)", sl_hit == True)
    
    # Short 포지션 - SL 미히트
    sl_no_hit = manager.check_sl_hit(pos_short, high=50900, low=50500)
    result.ok("Short SL 미히트 (high=50900 < SL=51000)", sl_no_hit == False)
    
    # None 포지션
    sl_none = manager.check_sl_hit(None, high=50000, low=49000)
    result.ok("None 포지션 → False", sl_none == False)
    
    # ===========================================
    # 3. 추가 진입 조건 테스트
    # ===========================================
    print("\n[3. 추가 진입 조건]")
    
    # Long 포지션 - RSI < 45 → 추가 진입
    pos_long = MockPosition(side='Long', add_count=0)
    should_add = manager.should_add_position(pos_long, current_rsi=40)
    result.ok("Long RSI=40 < 45 → 추가", should_add == True)
    
    # Long 포지션 - RSI > 45 → 추가 안함
    should_not_add = manager.should_add_position(pos_long, current_rsi=50)
    result.ok("Long RSI=50 > 45 → 미추가", should_not_add == False)
    
    # Short 포지션 - RSI > 55 → 추가 진입
    pos_short = MockPosition(side='Short', add_count=0)
    should_add = manager.should_add_position(pos_short, current_rsi=60)
    result.ok("Short RSI=60 > 55 → 추가", should_add == True)
    
    # Short 포지션 - RSI < 55 → 추가 안함
    should_not_add = manager.should_add_position(pos_short, current_rsi=50)
    result.ok("Short RSI=50 < 55 → 미추가", should_not_add == False)
    
    # max_adds 초과
    pos_maxed = MockPosition(side='Long', add_count=2)  # max_adds=2
    should_not_add = manager.should_add_position(pos_maxed, current_rsi=40)
    result.ok("add_count >= max_adds → 미추가", should_not_add == False)
    
    # enable_pullback=False
    manager_no_pullback = PositionManager(
        exchange=mock_exchange,
        strategy_params={'enable_pullback': False}
    )
    should_not_add = manager_no_pullback.should_add_position(pos_long, current_rsi=40)
    result.ok("enable_pullback=False → 미추가", should_not_add == False)
    
    # ===========================================
    # 4. 트레일링 SL 업데이트 테스트
    # ===========================================
    print("\n[4. 트레일링 SL 업데이트]")
    
    # dry_run=False로 실제 호출
    mock_exchange_real = MockExchange()
    manager_real = PositionManager(
        exchange=mock_exchange_real,
        strategy_params={},
        dry_run=False
    )
    
    success = manager_real.update_trailing_sl(new_sl=50500)
    result.ok("트레일링 SL 업데이트 성공", success == True)
    result.ok("거래소 호출 확인", 50500 in mock_exchange_real.sl_updates, f"호출 기록: {mock_exchange_real.sl_updates}")
    
    # dry_run 모드
    manager_dry = PositionManager(
        exchange=mock_exchange,
        strategy_params={},
        dry_run=True
    )
    success_dry = manager_dry.update_trailing_sl(new_sl=50500)
    result.ok("dry_run SL 업데이트 성공", success_dry == True)
    
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
    result = run_position_manager_tests()
    sys.exit(0 if result.failed == 0 else 1)
