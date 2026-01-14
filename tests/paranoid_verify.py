#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
극한 검증 모드 (Paranoid Verification)
- 모든 모듈 임포트 테스트
- 기능 동작 테스트
- 위젯 로드 테스트
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import traceback

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI"))
os.chdir(PROJECT_ROOT)

class VerificationResult:
    def __init__(self):
        self.import_tests = []
        self.func_tests = []
        self.widget_tests = []
        
    def add_import(self, module, success, error=None):
        self.import_tests.append({"module": module, "ok": success, "error": error})
        
    def add_func(self, name, success, error=None):
        self.func_tests.append({"name": name, "ok": success, "error": error})
        
    def add_widget(self, name, success, error=None):
        self.widget_tests.append({"name": name, "ok": success, "error": error})

RESULT = VerificationResult()

def test_import(module_path):
    """모듈 임포트 테스트"""
    try:
        exec(f"from {module_path} import *")
        print(f"  ✅ {module_path}")
        RESULT.add_import(module_path, True)
        return True
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:100]}"
        print(f"  ❌ {module_path}")
        print(f"     → {err}")
        RESULT.add_import(module_path, False, err)
        return False

def test_func(name, func):
    """기능 테스트"""
    try:
        func()
        print(f"  ✅ {name}")
        RESULT.add_func(name, True)
        return True
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)[:100]}"
        print(f"  ❌ {name}")
        print(f"     → {err}")
        RESULT.add_func(name, False, err)
        return False

def run_verification():
    print("\n" + "="*70)
    print("🔬 극한 검증 모드 (Paranoid Verification)")
    print("="*70)
    print(f"⏰ 시작: {datetime.now()}\n")
    
    # ========================================
    # 1. Core 모듈 임포트 테스트
    # ========================================
    print("\n[1] Core 모듈 임포트 테스트")
    print("-"*40)
    
    core_modules = [
        "core.strategy_core",
        "core.optimizer", 
        "core.unified_backtest",
        "core.auto_scanner",
        "core.unified_bot",
        "core.batch_optimizer",
        "core.multi_symbol_backtest",
    ]
    for m in core_modules:
        test_import(m)
        
    # ========================================
    # 2. GUI 모듈 임포트 테스트
    # ========================================
    print("\n[2] GUI 모듈 임포트 테스트")
    print("-"*40)
    
    gui_modules = [
        "GUI.staru_main",
        "GUI.optimization_widget",
        "GUI.backtest_widget",
        "GUI.auto_pipeline_widget",
        "GUI.trading_dashboard",
        "GUI.data_manager",
        "GUI.settings_widget",
    ]
    for m in gui_modules:
        test_import(m)
        
    # ========================================
    # 3. Utils 모듈 임포트 테스트
    # ========================================
    print("\n[3] Utils 모듈 임포트 테스트")
    print("-"*40)
    
    utils_modules = [
        "utils.crypto",
        "utils.retry",
        "utils.state_manager",
        "utils.validators",
        "utils.health_check",
        "utils.updater",
        "utils.preset_manager",
        "utils.symbol_converter",
    ]
    for m in utils_modules:
        test_import(m)
        
    # ========================================
    # 4. Exchange 모듈 임포트 테스트
    # ========================================
    print("\n[4] Exchange 모듈 임포트 테스트")
    print("-"*40)
    
    exchange_modules = [
        "exchanges.bybit_exchange",
        "exchanges.binance_exchange",
        "exchanges.okx_exchange",
        "exchanges.bitget_exchange",
        "exchanges.bingx_exchange",
        "exchanges.upbit_exchange",
        "exchanges.bithumb_exchange",
        "exchanges.exchange_manager",
    ]
    for m in exchange_modules:
        test_import(m)
        
    # ========================================
    # 5. 기능 동작 테스트
    # ========================================
    print("\n[5] 기능 동작 테스트")
    print("-"*40)
    
    def test_data_manager():
        from GUI.data_manager import DataManager
        dm = DataManager()
        files = list(dm.cache_dir.glob("*.parquet"))
        assert len(files) > 0, f"No cache files found in {dm.cache_dir}"
        print(f"     (캐시 파일: {len(files)}개)")
        
    def test_strategy():
        from core.strategy_core import AlphaX7Core
        s = AlphaX7Core()
        assert s is not None
        
    def test_preset_manager():
        from utils.preset_manager import get_preset_manager
        pm = get_preset_manager()
        if pm:
            presets = pm.list_presets()
            print(f"     (프리셋: {len(presets)}개)")
            
    test_func("DataManager 로드", test_data_manager)
    test_func("AlphaX7Core 전략", test_strategy)
    test_func("PresetManager 로드", test_preset_manager)
    
    # ========================================
    # 6. 위젯 로드 테스트 (PyQt5 필요)
    # ========================================
    print("\n[6] 위젯 로드 테스트")
    print("-"*40)
    
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        
        def test_widget(name, widget_class):
            try:
                w = widget_class()
                assert w is not None
                print(f"  ✅ {name}")
                RESULT.add_widget(name, True)
                return True
            except Exception as e:
                err = f"{type(e).__name__}: {str(e)[:80]}"
                print(f"  ❌ {name}")
                print(f"     → {err}")
                RESULT.add_widget(name, False, err)
                return False
                
        # OptimizationWidget
        try:
            from GUI.optimization_widget import OptimizationWidget
            test_widget("OptimizationWidget", OptimizationWidget)
        except Exception as e:
            RESULT.add_widget("OptimizationWidget", False, str(e)[:80])
            
        # BacktestWidget
        try:
            from GUI.backtest_widget import BacktestWidget
            test_widget("BacktestWidget", BacktestWidget)
        except Exception as e:
            RESULT.add_widget("BacktestWidget", False, str(e)[:80])
            
        # AutoPipelineWidget
        try:
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            test_widget("AutoPipelineWidget", AutoPipelineWidget)
        except Exception as e:
            RESULT.add_widget("AutoPipelineWidget", False, str(e)[:80])
            
    except ImportError:
        print("  ⚠ PyQt5 not available, skipping widget tests")
        
    # ========================================
    # 리포트 생성
    # ========================================
    generate_report()
    
def generate_report():
    print("\n" + "="*70)
    print("📊 극한 검증 리포트")
    print("="*70)
    
    # 통계
    import_ok = sum(1 for t in RESULT.import_tests if t["ok"])
    import_fail = len(RESULT.import_tests) - import_ok
    
    func_ok = sum(1 for t in RESULT.func_tests if t["ok"])
    func_fail = len(RESULT.func_tests) - func_ok
    
    widget_ok = sum(1 for t in RESULT.widget_tests if t["ok"])
    widget_fail = len(RESULT.widget_tests) - widget_ok
    
    print(f"\n[임포트 테스트] {import_ok}/{len(RESULT.import_tests)} 성공")
    if import_fail > 0:
        print("  실패 목록:")
        for t in RESULT.import_tests:
            if not t["ok"]:
                print(f"    - {t['module']}: {t['error']}")
                
    print(f"\n[기능 테스트] {func_ok}/{len(RESULT.func_tests)} 성공")
    if func_fail > 0:
        print("  실패 목록:")
        for t in RESULT.func_tests:
            if not t["ok"]:
                print(f"    - {t['name']}: {t['error']}")
                
    print(f"\n[위젯 테스트] {widget_ok}/{len(RESULT.widget_tests)} 성공")
    if widget_fail > 0:
        print("  실패 목록:")
        for t in RESULT.widget_tests:
            if not t["ok"]:
                print(f"    - {t['name']}: {t['error']}")
                
    total_fail = import_fail + func_fail + widget_fail
    print(f"\n{'='*70}")
    if total_fail == 0:
        print("✅ 전체 검증 통과!")
    else:
        print(f"❌ {total_fail}개 실패 발견")
        
    # 파일 저장
    report_path = PROJECT_ROOT / "tests" / "gui_report" / "paranoid_verification.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 극한 검증 리포트\n\n")
        f.write(f"- 시간: {datetime.now()}\n\n")
        
        f.write("## 임포트 테스트\n")
        f.write(f"- 성공: {import_ok}/{len(RESULT.import_tests)}\n\n")
        if import_fail > 0:
            f.write("### 실패 목록\n")
            for t in RESULT.import_tests:
                if not t["ok"]:
                    f.write(f"- `{t['module']}`: {t['error']}\n")
                    
        f.write("\n## 기능 테스트\n")
        f.write(f"- 성공: {func_ok}/{len(RESULT.func_tests)}\n\n")
        if func_fail > 0:
            f.write("### 실패 목록\n")
            for t in RESULT.func_tests:
                if not t["ok"]:
                    f.write(f"- `{t['name']}`: {t['error']}\n")
                    
        f.write("\n## 위젯 테스트\n")
        f.write(f"- 성공: {widget_ok}/{len(RESULT.widget_tests)}\n\n")
        if widget_fail > 0:
            f.write("### 실패 목록\n")
            for t in RESULT.widget_tests:
                if not t["ok"]:
                    f.write(f"- `{t['name']}`: {t['error']}\n")
                    
    print(f"\n📄 리포트 저장: {report_path}")
    
    return total_fail == 0

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
