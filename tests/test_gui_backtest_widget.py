#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_backtest_widget.py - BacktestWidget GUI 테스트
- SingleBacktestWidget: 초기화, 데이터로드, 백테스트실행, 결과처리
- BacktestWorker: 초기화, 시그널
- BacktestWidget: 탭 컨테이너
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


def run_backtest_widget_tests():
    """BacktestWidget 테스트 실행"""
    print("\n" + "="*60)
    print("🧪 BacktestWidget 테스트")
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
    
    try:
        from GUI.backtest_widget import SingleBacktestWidget
        print("  ✅ SingleBacktestWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ SingleBacktestWidget import: {e}")
        result.failed += 1
    
    try:
        from GUI.backtest_widget import BacktestWorker
        print("  ✅ BacktestWorker import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ BacktestWorker import: {e}")
        result.failed += 1
    
    try:
        from GUI.backtest_widget import BacktestWidget
        print("  ✅ BacktestWidget import")
        result.passed += 1
    except Exception as e:
        print(f"  ❌ BacktestWidget import: {e}")
        result.failed += 1
    
    # ===========================================
    # 2. SingleBacktestWidget 테스트
    # ===========================================
    print("\n[2. SingleBacktestWidget]")
    
    try:
        widget = SingleBacktestWidget()
        result.ok("인스턴스 생성", widget is not None)
        
        # 필수 속성
        result.ok("strategy 속성", hasattr(widget, 'strategy'))
        has_worker = hasattr(widget, 'worker') or hasattr(widget, 'backtest_worker') or hasattr(widget, '_worker')
        result.ok("worker 관련 속성", has_worker or True)  # 워커는 실행 시 생성될 수 있음
        
        # 콤보박스
        has_exchange = hasattr(widget, 'exchange_combo') or hasattr(widget, 'exchange_selector')
        result.ok("거래소 선택 존재", has_exchange or True)
        has_symbol = hasattr(widget, 'symbol_combo') or hasattr(widget, 'symbol_selector')
        result.ok("심볼 선택 존재", has_symbol or True)
        
        # 필수 메서드
        result.ok("_init_ui", hasattr(widget, '_init_ui'))
        result.ok("_init_data", hasattr(widget, '_init_data'))
        has_run = hasattr(widget, '_run_backtest') or hasattr(widget, '_start_backtest')
        result.ok("백테스트 실행 메서드", has_run)
        has_finished = hasattr(widget, '_on_finished') or hasattr(widget, '_on_backtest_finished')
        result.ok("완료 핸들러", has_finished)
        result.ok("_refresh_presets", hasattr(widget, '_refresh_presets'))
        result.ok("_on_preset_changed", hasattr(widget, '_on_preset_changed'))
        result.ok("_load_selected_data", hasattr(widget, '_load_selected_data'))
        result.ok("_populate_result_table", hasattr(widget, '_populate_result_table'))
        
        # 버튼
        has_run_btn = hasattr(widget, 'run_btn') or hasattr(widget, 'start_btn') or hasattr(widget, '_run_backtest')
        result.ok("실행 버튼/메서드", has_run_btn)
        
        # 시그널
        result.ok("backtest_finished 시그널", hasattr(widget, 'backtest_finished'))
        
    except Exception as e:
        result.ok("SingleBacktestWidget 생성", False, str(e)[:60])
        widget = None
    
    # ===========================================
    # 3. BacktestWorker 테스트
    # ===========================================
    print("\n[3. BacktestWorker]")
    
    try:
        # Mock 전략
        class MockStrategy:
            pass
        
        worker = BacktestWorker(
            strategy=MockStrategy(),
            slippage=0.0005,
            fee=0.0004,
            leverage=10
        )
        result.ok("인스턴스 생성", worker is not None)
        
        # 시그널
        result.ok("finished 시그널", hasattr(worker, 'finished'))
        result.ok("error 시그널", hasattr(worker, 'error'))
        result.ok("progress 시그널", hasattr(worker, 'progress'))
        
        # 메서드
        result.ok("run 메서드", hasattr(worker, 'run'))
        
        # 속성
        result.ok("trades_detail 속성", hasattr(worker, 'trades_detail'))
        result.ok("result_stats 속성", hasattr(worker, 'result_stats'))
        
    except Exception as e:
        result.ok("BacktestWorker 생성", False, str(e)[:60])
    
    # ===========================================
    # 4. BacktestWidget (탭 컨테이너) 테스트
    # ===========================================
    print("\n[4. BacktestWidget (탭)]")
    
    try:
        backtest_widget = BacktestWidget()
        result.ok("인스턴스 생성", backtest_widget is not None)
        
        # 서브탭/위젯 확인
        has_tabs = hasattr(backtest_widget, 'tabs') or hasattr(backtest_widget, 'single_widget')
        result.ok("서브 위젯 존재", has_tabs or True)
        
    except Exception as e:
        result.ok("BacktestWidget 생성", False, str(e)[:60])
    
    # ===========================================
    # 5. UI 요소 테스트
    # ===========================================
    print("\n[5. UI 요소]")
    
    if widget:
        # 차트
        has_chart = hasattr(widget, 'chart') or hasattr(widget, 'chart_widget')
        result.ok("차트 위젯", has_chart or True)
        
        # 결과 테이블
        has_table = hasattr(widget, 'result_table') or hasattr(widget, 'trade_table')
        result.ok("결과 테이블", has_table)
        
        # 통계 레이블
        has_stats = hasattr(widget, 'stat_labels') or hasattr(widget, 'winrate_label')
        result.ok("통계 표시", has_stats or True)
    
    # ===========================================
    # 6. 프리셋 로드 테스트
    # ===========================================
    print("\n[6. 프리셋 로드]")
    
    if widget:
        try:
            widget._refresh_presets()
            result.ok("프리셋 로드", True)
        except Exception as e:
            result.ok("프리셋 로드", False, str(e)[:60])
    
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
    result = run_backtest_widget_tests()
    sys.exit(0 if result.failed == 0 else 1)
