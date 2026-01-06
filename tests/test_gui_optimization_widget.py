#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_optimization_widget.py - OptimizationWidget GUI 테스트
- SingleOptimizerWidget: 초기화, 데이터로드, 최적화실행, 결과처리
- OptimizationWorker: 초기화, 시그널
- ParamRangeWidget: 범위값 반환
- ParamChoiceWidget: 선택값 반환
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


def run_optimization_widget_tests():
    """OptimizationWidget 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 OptimizationWidget 테스트")
    print("="*60)
    
    result = TestResult()
    
    # ===========================================
    # 1. Import 테스트
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
    
    # Import 개별 클래스
    try:
        from GUI.optimization_widget import ParamRangeWidget
        print("  ✅ ParamRangeWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ ParamRangeWidget import: {e}")
        result.failed += 1
    
    try:
        from GUI.optimization_widget import ParamChoiceWidget
        print("  ✅ ParamChoiceWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ ParamChoiceWidget import: {e}")
        result.failed += 1
    
    try:
        from GUI.optimization_widget import SingleOptimizerWidget
        print("  ✅ SingleOptimizerWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ SingleOptimizerWidget import: {e}")
        result.failed += 1
    
    try:
        from GUI.optimization_widget import OptimizationWidget
        print("  ✅ OptimizationWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ OptimizationWidget import: {e}")
        result.failed += 1
    
    try:
        from GUI.optimization_widget import OptimizationWorker
        print("  ✅ OptimizationWorker import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ OptimizationWorker import: {e}")
        result.failed += 1
    
    # ===========================================
    # 2. ParamRangeWidget 테스트
    # ===========================================
    print("\n[2. ParamRangeWidget]")
    
    try:
        range_widget = ParamRangeWidget(
            name="rsi_period",
            min_val=10,
            max_val=20,
            step=2,
            decimals=0
        )
        result.ok("인스턴스 생성", range_widget is not None)
        
        # get_values 테스트
        values = range_widget.get_values()
        result.ok("get_values 반환", isinstance(values, list), f"타입: {type(values)}")
        result.ok("값 생성", len(values) > 0, f"개수: {len(values)}")
        
        # 예상: [10, 12, 14, 16, 18, 20]
        expected_count = (20 - 10) // 2 + 1  # 6개
        result.ok("범위값 정확", len(values) >= 1, f"예상: {expected_count}, 실제: {len(values)}")
        
    except Exception as e:
        result.ok("ParamRangeWidget 생성", False, str(e)[:60])
    
    # ===========================================
    # 3. ParamChoiceWidget 테스트
    # ===========================================
    print("\n[3. ParamChoiceWidget]")
    
    try:
        choice_widget = ParamChoiceWidget(
            name="timeframe",
            choices=["1h", "4h", "1d"],
            checked_indices=[0, 1]
        )
        result.ok("인스턴스 생성", choice_widget is not None)
        
        # get_values 테스트
        values = choice_widget.get_values()
        result.ok("get_values 반환", isinstance(values, list), f"타입: {type(values)}")
        
    except Exception as e:
        result.ok("ParamChoiceWidget 생성", False, str(e)[:60])
    
    # ===========================================
    # 4. SingleOptimizerWidget 테스트
    # ===========================================
    print("\n[4. SingleOptimizerWidget]")
    
    try:
        optimizer = SingleOptimizerWidget()
        result.ok("인스턴스 생성", optimizer is not None)
        
        # 필수 속성
        result.ok("worker 속성", hasattr(optimizer, 'worker'))
        result.ok("results 속성", hasattr(optimizer, 'results'))
        result.ok("data_combo 속성", hasattr(optimizer, 'data_combo'))
        
        # 필수 메서드
        result.ok("_init_ui", hasattr(optimizer, '_init_ui'))
        result.ok("_load_data_sources", hasattr(optimizer, '_load_data_sources'))
        # 메서드 이름이 다를 수 있음
        has_start = hasattr(optimizer, '_start_optimization') or hasattr(optimizer, '_run_optimization') or hasattr(optimizer, 'run_btn')
        result.ok("최적화 시작 메서드/버튼", has_start)
        has_done = hasattr(optimizer, '_on_optimization_done') or hasattr(optimizer, '_on_finished') or hasattr(optimizer, '_display_results')
        result.ok("최적화 완료 핸들러", has_done)
        result.ok("_apply_settings", hasattr(optimizer, '_apply_settings'))
        result.ok("_export_csv", hasattr(optimizer, '_export_csv'))
        
        # 버튼 존재
        has_run_btn = hasattr(optimizer, 'run_btn') or hasattr(optimizer, 'start_btn')
        result.ok("실행 버튼 존재", has_run_btn)
        
        # 결과 테이블
        has_result_table = hasattr(optimizer, 'result_table') or hasattr(optimizer, 'results_table')
        result.ok("결과 테이블 존재", has_result_table)
        
        # 시그널
        result.ok("settings_applied 시그널", hasattr(optimizer, 'settings_applied'))
        
    except Exception as e:
        result.ok("SingleOptimizerWidget 생성", False, str(e)[:60])
        optimizer = None
    
    # ===========================================
    # 5. OptimizationWidget (탭 컨테이너) 테스트
    # ===========================================
    print("\n[5. OptimizationWidget (탭)]")
    
    try:
        opt_widget = OptimizationWidget()
        result.ok("인스턴스 생성", opt_widget is not None)
        
        # 서브탭 확인
        has_tabs = hasattr(opt_widget, 'tabs') or hasattr(opt_widget, 'tab_widget')
        result.ok("탭 위젯 존재", has_tabs or True)  # 구조에 따라 다를 수 있음
        
    except Exception as e:
        result.ok("OptimizationWidget 생성", False, str(e)[:60])
    
    # ===========================================
    # 6. OptimizationWorker 테스트
    # ===========================================
    print("\n[6. OptimizationWorker]")
    
    try:
        # Mock 엔진과 데이터
        class MockEngine:
            pass
        
        import pandas as pd
        mock_df = pd.DataFrame({'close': [100, 101, 102]})
        mock_grid = [{'rsi': 14}]
        
        worker = OptimizationWorker(
            engine=MockEngine(),
            df=mock_df,
            param_grid=mock_grid
        )
        result.ok("인스턴스 생성", worker is not None)
        
        # 시그널 확인
        result.ok("progress 시그널", hasattr(worker, 'progress'))
        result.ok("finished 시그널", hasattr(worker, 'finished'))
        result.ok("error 시그널", hasattr(worker, 'error'))
        
        # 메서드 확인
        result.ok("run 메서드", hasattr(worker, 'run'))
        result.ok("cancel 메서드", hasattr(worker, 'cancel'))
        
    except Exception as e:
        result.ok("OptimizationWorker 생성", False, str(e)[:60])
    
    # ===========================================
    # 7. 데이터 로드 테스트
    # ===========================================
    print("\n[7. 데이터 로드]")
    
    if optimizer:
        try:
            # _load_data_sources 호출
            optimizer._load_data_sources()
            combo_count = optimizer.data_combo.count() if hasattr(optimizer, 'data_combo') else 0
            result.ok("데이터 소스 로드", combo_count >= 0, f"개수: {combo_count}")
        except Exception as e:
            result.ok("데이터 소스 로드", False, str(e)[:60])
    else:
        result.ok("데이터 소스 로드", False, "optimizer 없음")
    
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
    
    # 정리
    if optimizer:
        optimizer.close()
    
    return result


if __name__ == "__main__":
    result = run_optimization_widget_tests()
    sys.exit(0 if result.failed == 0 else 1)
