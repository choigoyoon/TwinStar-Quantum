#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_strategy_selector_widget.py - StrategySelectorWidget GUI 테스트
- StrategyCard: 초기화, 선택 상태 변경
- StrategySelectorWidget: 초기화, 전략 로드, 필터링, 선택
"""
import sys
import os
from pathlib import Path
import logging
from typing import Any, cast

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def ok(self, name, condition, msg=""):
        if condition:
            print(f"  ✅ {name}")
            self.passed += 1
        else:
            print(f"  ❌ {name}: {msg}")
            self.failed += 1
            self.errors.append(f"{name}: {msg}")


def run_strategy_selector_tests():
    """StrategySelectorWidget 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 StrategySelectorWidget 테스트")
    print("="*60)
    
    result = TestResult()
    
    # ===========================================
    # 1. Import
    # ===========================================
    print("\n[1. Import]")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("  ✅ PyQt5 import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ PyQt5 import: {e}")
        result.failed += 1
        return result
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        from GUI.strategy_selector_widget import StrategySelectorWidget, StrategyCard
        print("  ✅ StrategySelectorWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ StrategySelectorWidget import: {e}")
        result.failed += 1
        return result
    
    try:
        from strategies.strategy_loader import StrategyInfo
        print("  ✅ StrategyInfo import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ StrategyInfo import: {e}")
        result.failed += 1
    
    # ===========================================
    # 2. StrategyCard
    # ===========================================
    print("\n[2. StrategyCard]")
    
    try:
        # Mock StrategyInfo
        class MockInfo:
            def __init__(self):
                self.strategy_id = "test_strat"  # id -> strategy_id
                self.name = "Test Strategy"
                self.description = "Test Description"
                self.tier_required = "basic"  # tier -> tier_required
                self.version = "1.0"
                self.author = "Test"
        
        card = StrategyCard(cast(Any, MockInfo()))
        result.ok("인스턴스 생성", card is not None)
        
        # 메서드 확인
        result.ok("_init_ui", hasattr(card, '_init_ui'))
        result.ok("set_selected", hasattr(card, 'set_selected'))
        
        # 시그널
        result.ok("selected 시그널", hasattr(card, 'selected'))
        
        # 선택 상태 변경
        card.set_selected(True)
        result.ok("선택 상태 변경 (True)", card._is_selected)
        
    except Exception as e:
        result.ok("StrategyCard 생성", False, str(e)[:60])
    
    # ===========================================
    # 3. StrategySelectorWidget
    # ===========================================
    print("\n[3. StrategySelectorWidget]")
    
    try:
        widget = StrategySelectorWidget(user_tier="basic")
        result.ok("인스턴스 생성", widget is not None)
        
        # 메서드 확인
        result.ok("_init_ui", hasattr(widget, '_init_ui'))
        result.ok("_load_strategies", hasattr(widget, '_load_strategies'))
        result.ok("_filter_strategies", hasattr(widget, '_filter_strategies'))
        result.ok("_on_card_selected", hasattr(widget, '_on_card_selected'))
        result.ok("_load_selected_strategy", hasattr(widget, '_load_selected_strategy'))
        result.ok("get_selected_strategy", hasattr(widget, 'get_selected_strategy'))
        result.ok("set_user_tier", hasattr(widget, 'set_user_tier'))
        
        # 시그널
        result.ok("strategy_selected 시그널", hasattr(widget, 'strategy_selected'))
        
    except Exception as e:
        result.ok("StrategySelectorWidget 생성", False, str(e)[:60])
        widget = None
        
    # ===========================================
    # 4. 기능 테스트
    # ===========================================
    print("\n[4. 기능 테스트]")
    
    if widget:
        try:
            # 티어 변경
            widget.set_user_tier("premium")
            result.ok("티어 변경", widget._user_tier == "premium")
        except Exception as e:
            result.ok("티어 변경", False, str(e)[:60])
            
        try:
            # 필터링 (메서드 호출 확인)
            widget._filter_strategies("premium")
            result.ok("필터링 호출", True)
        except Exception as e:
            result.ok("필터링 호출", False, str(e)[:60])

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
    
    if widget:
        widget.close()
    
    return result


if __name__ == "__main__":
    result = run_strategy_selector_tests()
    sys.exit(0 if result.failed == 0 else 1)
