#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_developer_mode_widget.py - DeveloperModeWidget GUI 테스트
- DeveloperModeWidget: 초기화, 탭 구성, 최적화 실행, 파라미터 관리
"""
import sys
import os
from pathlib import Path
import logging

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


def run_developer_mode_tests():
    """DeveloperModeWidget 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 DeveloperModeWidget 테스트")
    print("="*60)
    
    result = TestResult()
    
    # ===========================================
    # 1. Import
    # ===========================================
    print("\n[1. Import]")
    
    try:
        from PyQt5.QtWidgets import QApplication
        print("  ✅ PyQt5 import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ PyQt5 import: {e}")
        result.failed += 1
        return result
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        from GUI.developer_mode_widget import DeveloperModeWidget
        print("  ✅ DeveloperModeWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ DeveloperModeWidget import: {e}")
        result.failed += 1
    
    # ===========================================
    # 2. DeveloperModeWidget
    # ===========================================
    print("\n[2. DeveloperModeWidget]")
    
    try:
        widget = DeveloperModeWidget()
        result.ok("인스턴스 생성", widget is not None)
        
        # 탭 메서드
        result.ok("_create_param_optimizer_tab", hasattr(widget, '_create_param_optimizer_tab'))
        result.ok("_create_log_tab", hasattr(widget, '_create_log_tab'))
        result.ok("_create_system_tab", hasattr(widget, '_create_system_tab'))
        
        # 최적화 로직 메서드
        result.ok("_run_backtest", hasattr(widget, '_run_backtest'))
        result.ok("_run_auto_optimize", hasattr(widget, '_run_auto_optimize'))
        
        # 파라미터 관리 메서드
        result.ok("_apply_params", hasattr(widget, '_apply_params'))
        result.ok("_load_best_params", hasattr(widget, '_load_best_params'))
        result.ok("_save_params", hasattr(widget, '_save_params'))
        result.ok("_get_current_params", hasattr(widget, '_get_current_params'))
        result.ok("_on_result_selected", hasattr(widget, '_on_result_selected'))
        
    except Exception as e:
        result.ok("DeveloperModeWidget 생성", False, str(e)[:60])
        widget = None
        
    # ===========================================
    # 3. 기능 테스트
    # ===========================================
    print("\n[3. 기능 테스트]")
    
    if widget:
        try:
            params = widget._get_current_params()
            result.ok("파라미터 가져오기", isinstance(params, dict))
        except Exception as e:
            result.ok("파라미터 가져오기", False, str(e)[:60])
            
        try:
            widget._apply_params({})
            result.ok("파라미터 적용 (빈 값)", True)
        except Exception as e:
            result.ok("파라미터 적용", False, str(e)[:60])

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
    result = run_developer_mode_tests()
    sys.exit(0 if result.failed == 0 else 1)
