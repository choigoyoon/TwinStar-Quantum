"""
TwinStar Quantum - 전문 검증 시스템
1. 모듈 검증 (Module Verification)
2. 메서드 검증 (Method Verification)
3. 임포트 검증 (Import Verification)
4. GUI 검증 (GUI Component Verification)
5. 경로 검증 (Path Verification)
6. 의존성 검증 (Dependency Verification)
"""

import os
import sys
import ast
import json
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 프로젝트 루트 설정
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

class VerificationReport:
    """검증 결과 리포트"""
    def __init__(self):
        self.results = {
            'modules': {'passed': [], 'failed': []},
            'methods': {'passed': [], 'failed': []},
            'imports': {'passed': [], 'failed': []},
            'gui': {'passed': [], 'failed': []},
            'paths': {'passed': [], 'failed': []},
            'deps': {'passed': [], 'failed': []}
        }
    
    def add(self, category: str, name: str, passed: bool, error: Optional[str] = None):
        status = 'passed' if passed else 'failed'
        self.results[category][status].append({
            'name': name,
            'error': error
        })
    
    def summary(self) -> str:
        lines = ["\n" + "="*60, "📊 검증 결과 요약", "="*60]
        
        for cat, data in self.results.items():
            p = len(data['passed'])
            f = len(data['failed'])
            total = p + f
            pct = (p / total * 100) if total > 0 else 0
            status = "✅" if f == 0 else "❌"
            lines.append(f"{status} {cat.upper()}: {p}/{total} ({pct:.1f}%)")
        
        return "\n".join(lines)
    
    def failures(self) -> str:
        lines = ["\n" + "="*60, "❌ 실패 항목 상세", "="*60]
        
        for cat, data in self.results.items():
            if data['failed']:
                lines.append(f"\n[{cat.upper()}]")
                for item in data['failed']:
                    lines.append(f"  - {item['name']}: {item['error']}")
        
        return "\n".join(lines)


# ================================================================
# 1. 모듈 검증
# ================================================================

CORE_MODULES = [
    "core.auto_optimizer",
    "core.capital_manager",
    "core.multi_trader",
    "core.order_executor",
    "core.pnl_tracker",
    "core.strategy_core",
    "core.trade_common",
]

EXCHANGE_MODULES = [
    "exchanges.exchange_manager",
    "exchanges.binance_exchange",
    "exchanges.bybit_exchange",
    "exchanges.ws_handler",
]

UTIL_MODULES = [
    "utils.indicators",
    "utils.helpers",
    "utils.data_utils",
]

GUI_MODULES = [
    "GUI.staru_main",
    "GUI.trading_dashboard",
    "GUI.trading_tab_widget",
    "GUI.multi_trade_widget",
    "GUI.single_trade_widget",
]

def verify_modules(report: VerificationReport):
    """모듈 임포트 가능 여부 검증"""
    all_modules = CORE_MODULES + EXCHANGE_MODULES + UTIL_MODULES + GUI_MODULES
    
    for mod_name in all_modules:
        try:
            importlib.import_module(mod_name)
            report.add('modules', mod_name, True)
        except Exception as e:
            report.add('modules', mod_name, False, str(e)[:100])


# ================================================================
# 2. 메서드 검증
# ================================================================

REQUIRED_METHODS = {
    "core.multi_trader.MultiTrader": [
        "start", "stop", "_scan_signals", "_enter_position",
        "_has_preset", "_run_quick_optimize", "_get_adaptive_leverage",
        "_check_position", "_close_position", "get_stats"
    ],
    "core.auto_optimizer.AutoOptimizer": [
        "load_preset", "save_preset", "run_quick_optimize", "ensure_preset"
    ],
    "core.capital_manager.CapitalManager": [
        "get_trade_size", "update_after_trade", "switch_mode"
    ],
    "core.order_executor.OrderExecutor": [
        "place_order_with_retry", "close_position_with_retry", "set_leverage"
    ],
}

def verify_methods(report: VerificationReport):
    """필수 메서드 존재 여부 검증"""
    for class_path, methods in REQUIRED_METHODS.items():
        parts = class_path.rsplit(".", 1)
        mod_name, class_name = parts[0], parts[1]
        
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, class_name)
            
            for method in methods:
                if hasattr(cls, method):
                    report.add('methods', f"{class_name}.{method}", True)
                else:
                    report.add('methods', f"{class_name}.{method}", False, "메서드 없음")
        except Exception as e:
            for method in methods:
                report.add('methods', f"{class_name}.{method}", False, str(e)[:50])


# ================================================================
# 3. 임포트 검증 (AST 기반)
# ================================================================

def get_imports_from_file(filepath: Path) -> List[str]:
    """파일에서 임포트 목록 추출"""
    imports = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except Exception:

        pass
    return imports

def verify_imports(report: VerificationReport):
    """모든 파이썬 파일의 임포트 검증"""
    scan_dirs = ["core", "exchanges", "utils", "GUI", "strategies", "storage"]
    
    for folder in scan_dirs:
        folder_path = ROOT / folder
        if not folder_path.exists():
            continue
        
        for py_file in folder_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            imports = get_imports_from_file(py_file)
            rel_path = py_file.relative_to(ROOT)
            
            for imp in imports:
                # 내부 모듈만 검증
                if imp.startswith(("core", "exchanges", "utils", "GUI", "strategies", "storage")):
                    try:
                        importlib.import_module(imp)
                        report.add('imports', f"{rel_path}→{imp}", True)
                    except Exception:
                        report.add('imports', f"{rel_path}→{imp}", False, "임포트 실패")


# ================================================================
# 4. GUI 검증
# ================================================================

GUI_WIDGETS = {
    "GUI.trading_dashboard": "TradingDashboard",
    "GUI.trading_tab_widget": "TradingTabWidget",
    "GUI.multi_trade_widget": "MultiTradeWidget",
    "GUI.single_trade_widget": "SingleTradeWidget",
}

GUI_REQUIRED_ATTRS = {
    "TradingDashboard": ["_init_ui", "start_bot", "stop_bot"],
    "MultiTradeWidget": ["_init_ui", "_on_start", "_on_stop"],
}

def verify_gui(report: VerificationReport):
    """GUI 위젯 및 필수 속성 검증"""
    for mod_name, class_name in GUI_WIDGETS.items():
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, class_name, None)
            
            if cls is None:
                report.add('gui', f"{mod_name}.{class_name}", False, "클래스 없음")
                continue
            
            report.add('gui', f"{mod_name}.{class_name}", True)
            
            # 필수 속성 검증
            if class_name in GUI_REQUIRED_ATTRS:
                for attr in GUI_REQUIRED_ATTRS[class_name]:
                    if hasattr(cls, attr):
                        report.add('gui', f"{class_name}.{attr}", True)
                    else:
                        report.add('gui', f"{class_name}.{attr}", False, "속성 없음")
                        
        except Exception as e:
            report.add('gui', f"{mod_name}.{class_name}", False, str(e)[:50])


# ================================================================
# 5. 경로 검증
# ================================================================

def verify_paths(report: VerificationReport):
    """필수 경로 존재 여부 검증"""
    try:
        from paths import Paths
        
        required_paths = {
            "ROOT": getattr(Paths, 'ROOT', Paths.BASE), # ROOT가 없으면 BASE 사용
            "CONFIG": Paths.CONFIG,
            "PRESETS": Paths.PRESETS,
            "CACHE": Paths.CACHE,
            "LOGS": Paths.LOGS,
        }
        
        for name, path in required_paths.items():
            if isinstance(path, (Path, str)):
                report.add('paths', f"Paths.{name}", True)
            else:
                report.add('paths', f"Paths.{name}", False, f"타입: {type(path)}")
            
            # 디렉토리 존재 확인
            p_obj = Path(path)
            if p_obj.exists():
                report.add('paths', f"{name} 존재", True)
            else:
                report.add('paths', f"{name} 존재", False, "디렉토리 없음")
                    
    except Exception as e:
        report.add('paths', "Paths 모듈", False, str(e)[:50])


# ================================================================
# 6. 의존성 검증
# ================================================================

REQUIRED_DEPS = [
    "pandas", "numpy", "PyQt5", "requests", "websockets",
    "pybit", "ccxt", "ta", "json", "pathlib"
]

def verify_deps(report: VerificationReport):
    """외부 의존성 검증"""
    for dep in REQUIRED_DEPS:
        try:
            importlib.import_module(dep)
            report.add('deps', dep, True)
        except Exception:
            report.add('deps', dep, False, "설치 안 됨")


# ================================================================
# 메인 실행
# ================================================================

def main():
    print("="*60)
    print("🔍 TwinStar Quantum - 전문 검증 시스템")
    print("="*60)
    
    report = VerificationReport()
    
    print("\n[1/6] 모듈 검증...")
    verify_modules(report)
    
    print("[2/6] 메서드 검증...")
    verify_methods(report)
    
    print("[3/6] 임포트 검증...")
    verify_imports(report)
    
    print("[4/6] GUI 검증...")
    verify_gui(report)
    
    print("[5/6] 경로 검증...")
    verify_paths(report)
    
    print("[6/6] 의존성 검증...")
    verify_deps(report)
    
    # 결과 출력
    print(report.summary())
    
    # 실패 항목 상세
    failures = report.failures()
    if "failed" in str(report.results) and len(failures) > 100:
        print(failures)
    
    # JSON 저장
    output_file = ROOT / "tests" / "verify_result.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report.results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 상세 결과: {output_file}")
    
    # 종합 판정
    total_failed = sum(len(v['failed']) for v in report.results.values())
    if total_failed == 0:
        print("\n✅ 전체 검증 통과!")
        return 0
    else:
        print(f"\n❌ {total_failed}개 항목 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
