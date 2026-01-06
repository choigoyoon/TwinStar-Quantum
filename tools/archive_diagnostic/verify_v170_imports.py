import os
import sys
import py_compile
from pathlib import Path

PROJECT_ROOT = Path(r'C:\매매전략')
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def check_syntax(file_path):
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True, "OK"
    except Exception as e:
        return False, str(e)

def check_class_exists(module_path, class_name):
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("module.name", str(module_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return hasattr(module, class_name), "FOUND" if hasattr(module, class_name) else "MISSING"
    except Exception as e:
        return False, f"ERROR: {e}"

def verify():
    print("=" * 60)
    print(" TwinStar Quantum v1.7.0 임포트 & 문법 정밀 검증")
    print("=" * 60)

    # 1. 문법 검사 (Syntax Check)
    print("\n[1] 핵심 파일 문법 검사:")
    files_to_check = [
        PROJECT_ROOT / 'core' / 'multi_symbol_backtest.py',
        PROJECT_ROOT / 'core' / 'batch_optimizer.py',
        PROJECT_ROOT / 'GUI' / 'backtest_widget.py',
        PROJECT_ROOT / 'GUI' / 'optimization_widget.py',
        PROJECT_ROOT / 'GUI' / 'staru_main.py',
    ]
    
    for f in files_to_check:
        ok, msg = check_syntax(f)
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status} {f.relative_to(PROJECT_ROOT)} : {msg}")

    # 2. 신규 클래스 존재 확인
    print("\n[2] v1.7.0 신규 클래스 노출 확인:")
    classes_to_check = [
        (PROJECT_ROOT / 'GUI' / 'backtest_widget.py', 'SingleBacktestWidget'),
        (PROJECT_ROOT / 'GUI' / 'backtest_widget.py', 'MultiBacktestWidget'),
        (PROJECT_ROOT / 'GUI' / 'backtest_widget.py', 'BacktestWidget'), # 컨테이너
        (PROJECT_ROOT / 'GUI' / 'optimization_widget.py', 'SingleOptimizerWidget'),
        (PROJECT_ROOT / 'GUI' / 'optimization_widget.py', 'BatchOptimizerWidget'),
        (PROJECT_ROOT / 'GUI' / 'optimization_widget.py', 'OptimizationWidget'), # 컨테이너
    ]

    for f, cls in classes_to_check:
        ok, msg = check_class_exists(f, cls)
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status} {f.name} -> {cls} : {msg}")

    # 3. 내부 임포트 무결성 (GUI -> Core)
    print("\n[3] 내부 임포트 무결성 확인:")
    try:
        # 이 섹션은 실제 GUI 실행 없이 임포트가 가능한지 테스트
        print("  - BacktestWidget -> MultiSymbolBacktest...", end="")
        import GUI.backtest_widget
        print(" OK")
        
        print("  - OptimizationWidget -> BatchOptimizer...", end="")
        import GUI.optimization_widget
        print(" OK")
    except Exception as e:
        print(f" FAILED: {e}")

    print("\n" + "=" * 60)
    print(" 검증 완료")
    print("=" * 60)

if __name__ == "__main__":
    verify()
