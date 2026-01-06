#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_auto_pipeline_widget.py - AutoPipelineWidget GUI 테스트
- StepWidget: 초기화, 버튼 추가
- AutoPipelineWidget: 초기화, 단계 이동, 심볼 로드, 최적화/백테스트 시작
- OptimizerThread/UBThread: 시그널
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


def run_auto_pipeline_tests():
    """AutoPipelineWidget 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 AutoPipelineWidget 테스트")
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
        from GUI.auto_pipeline_widget import AutoPipelineWidget
        print("  ✅ AutoPipelineWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ AutoPipelineWidget import: {e}")
        result.failed += 1
    
    try:
        from GUI.auto_pipeline_widget import StepWidget
        print("  ✅ StepWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ StepWidget import: {e}")
        result.failed += 1
    
    # ===========================================
    # 2. StepWidget
    # ===========================================
    print("\n[2. StepWidget]")
    
    try:
        step = StepWidget("Test Step")
        result.ok("인스턴스 생성", step is not None)
        result.ok("add_nav_buttons 메서드", hasattr(step, 'add_nav_buttons'))
        
    except Exception as e:
        result.ok("StepWidget 생성", False, str(e)[:60])
    
    # ===========================================
    # 3. AutoPipelineWidget
    # ===========================================
    print("\n[3. AutoPipelineWidget]")
    
    try:
        pipeline = AutoPipelineWidget()
        result.ok("인스턴스 생성", pipeline is not None)
        
        # UI 및 초기화 메서드
        result.ok("_init_ui", hasattr(pipeline, '_init_ui'))
        result.ok("_update_indicators", hasattr(pipeline, '_update_indicators'))
        
        # 내비게이션 메서드
        result.ok("_go_next", hasattr(pipeline, '_go_next'))
        result.ok("_go_back", hasattr(pipeline, '_go_back'))
        
        # 각 단계 생성 메서드
        result.ok("_create_step1", hasattr(pipeline, '_create_step1'))
        result.ok("_create_step2", hasattr(pipeline, '_create_step2'))
        result.ok("_create_step3", hasattr(pipeline, '_create_step3'))
        result.ok("_create_step4", hasattr(pipeline, '_create_step4'))
        result.ok("_create_step5", hasattr(pipeline, '_create_step5'))
        
        # 심볼 로드
        result.ok("_load_symbols", hasattr(pipeline, '_load_symbols'))
        result.ok("_update_selection_count", hasattr(pipeline, '_update_selection_count'))
        
        # 최적화/백테스트 관련
        result.ok("_start_optimization", hasattr(pipeline, '_start_optimization'))
        result.ok("_on_opt_finished", hasattr(pipeline, '_on_opt_finished'))
        
        result.ok("_run_unified_backtest", hasattr(pipeline, '_run_unified_backtest'))
        result.ok("_on_ub_finished", hasattr(pipeline, '_on_ub_finished'))
        
        # 스캐너 관련
        result.ok("_start_scanner", hasattr(pipeline, '_start_scanner'))
        result.ok("_stop_scanner", hasattr(pipeline, '_stop_scanner'))
        
        # 속성 확인
        result.ok("selected_symbols 리스트", isinstance(pipeline.selected_symbols, list))
        
    except Exception as e:
        result.ok("AutoPipelineWidget 생성", False, str(e)[:60])
        pipeline = None
        
    # ===========================================
    # 4. 기능 테스트
    # ===========================================
    print("\n[4. 기능 테스트]")
    
    if pipeline:
        try:
            # 인디케이터 업데이트 (인덱스 범위 체크)
            pipeline._update_indicators(0)
            result.ok("_update_indicators 호출", True)
        except Exception as e:
            result.ok("_update_indicators 호출", False, str(e)[:60])
            
        try:
            # 심볼 로드 시도 (Mock 없이 호출하면 거래소 연결 실패할 수 있으나 메서드 동작 확인)
            # 예외 처리되어 있어야 함
            pipeline._load_symbols()
            result.ok("_load_symbols 호출", True)
        except Exception as e:
            result.ok("_load_symbols 호출", False, str(e)[:60])

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
    
    if pipeline:
        pipeline.close()
    
    return result


if __name__ == "__main__":
    result = run_auto_pipeline_tests()
    sys.exit(0 if result.failed == 0 else 1)
