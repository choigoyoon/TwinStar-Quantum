"""
TwinStar-Quantum 프로덕션 준비 검증 스크립트

6개 카테고리 검증:
1. 진입점 (Entry Points)
2. Import 무결성 (Import Integrity)
3. 설정 파일 (Config Files)
4. 스토리지 초기화 (Storage Init)
5. SSOT 준수 (SSOT Compliance)
6. GUI 실행 가능성 (GUI Launch)

실행: python tools/verify_production_ready.py
"""

import os
import sys
from pathlib import Path
from typing import Tuple

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_entry_points() -> Tuple[bool, str]:
    """진입점 확인: run_gui.py, web/run_server.py"""

    required_files = [
        'run_gui.py',
        'web/run_server.py',
        'web/backend/main.py'
    ]

    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)

    if missing:
        return False, f"Missing entry points: {', '.join(missing)}"

    return True, "All entry points exist"


def check_import_integrity() -> Tuple[bool, str]:
    """Import 무결성 확인: 18개 핵심 모듈"""

    critical_imports = [
        # Config
        ('config.constants', 'EXCHANGE_INFO'),
        ('config.parameters', 'DEFAULT_PARAMS'),

        # Utils (SSOT)
        ('utils.indicators', 'calculate_rsi'),
        ('utils.metrics', 'calculate_backtest_metrics'),
        ('utils.logger', 'get_module_logger'),

        # Core
        ('core.unified_bot', 'UnifiedBot'),
        ('core.strategy_core', 'AlphaX7Core'),
        ('core.data_manager', 'BotDataManager'),
        ('core.optimizer', 'BacktestOptimizer'),
        ('core.order_executor', 'OrderExecutor'),
        ('core.position_manager', 'PositionManager'),

        # Exchanges
        ('exchanges.base_exchange', 'BaseExchange'),
        ('exchanges.bybit_exchange', 'BybitExchange'),
        ('exchanges.binance_exchange', 'BinanceExchange'),

        # GUI & UI
        ('GUI.staru_main', 'StarUWindow'),
        ('ui.design_system.tokens', 'Colors'),
        ('ui.widgets.backtest.main', 'BacktestWidget'),
        ('ui.widgets.optimization.main', 'OptimizationWidget'),
    ]

    failed = []
    for module_name, attr_name in critical_imports:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            if not hasattr(module, attr_name):
                failed.append(f"{module_name}.{attr_name} (attribute missing)")
        except ImportError as e:
            failed.append(f"{module_name} ({str(e)})")
        except Exception as e:
            failed.append(f"{module_name} (error: {str(e)})")

    if failed:
        return False, f"Import failures ({len(failed)}/18):\n  " + "\n  ".join(failed[:5])

    return True, f"All {len(critical_imports)} critical imports successful"


def check_config_files() -> Tuple[bool, str]:
    """설정 파일 확인"""

    required_configs = [
        'config/parameters.py',
        'config/constants/__init__.py',
        'config/constants/exchanges.py',
        'config/constants/timeframes.py',
        'config/constants/trading.py',
        'config/constants/grades.py',
        'config/constants/paths.py',
        'requirements.txt',
        '.gitignore',
        'CLAUDE.md'
    ]

    missing = []
    for config_path in required_configs:
        if not Path(config_path).exists():
            missing.append(config_path)

    if missing:
        return False, f"Missing configs ({len(missing)}/10): {', '.join(missing[:3])}"

    return True, "All 10 config files exist"


def check_storage_init() -> Tuple[bool, str]:
    """스토리지 디렉토리 확인"""

    required_dirs = [
        'data',
        'data/cache',
        'storage',
        'logs'
    ]

    missing = []
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            # 디렉토리 생성 시도
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                missing.append(f"{dir_path} (create failed: {e})")
        elif not path.is_dir():
            missing.append(f"{dir_path} (not a directory)")

    if missing:
        return False, f"Storage issues: {', '.join(missing)}"

    return True, "All storage directories exist or created"


def check_ssot_compliance() -> Tuple[bool, str]:
    """SSOT 준수 확인: indicators, metrics, parameters"""

    ssot_modules = [
        ('utils/indicators.py', ['calculate_rsi', 'calculate_atr', 'calculate_macd', 'add_all_indicators']),
        ('utils/incremental_indicators.py', ['IncrementalEMA', 'IncrementalRSI', 'IncrementalATR']),
        ('utils/metrics.py', ['calculate_mdd', 'calculate_profit_factor', 'calculate_backtest_metrics']),
        ('config/parameters.py', ['DEFAULT_PARAMS', 'PARAM_RANGES_BY_MODE', 'get_param_range_by_mode'])
    ]

    issues = []

    for file_path, required_attrs in ssot_modules:
        path = Path(file_path)
        if not path.exists():
            issues.append(f"{file_path} (file missing)")
            continue

        # 파일 내용에서 함수/클래스 정의 확인
        try:
            content = path.read_text(encoding='utf-8')
            for attr in required_attrs:
                if f"def {attr}" not in content and f"class {attr}" not in content and f"{attr} =" not in content:
                    issues.append(f"{file_path}::{attr} (not found)")
        except Exception as e:
            issues.append(f"{file_path} (read error: {e})")

    if issues:
        return False, f"SSOT issues ({len(issues)}): " + ", ".join(issues[:3])

    return True, "All SSOT modules compliant (v7.15-v7.18)"


def check_gui_launch() -> Tuple[bool, str]:
    """GUI 실행 가능성 확인 (import만 테스트)"""

    try:
        # PyQt6 설치 확인
        import PyQt6
        from PyQt6.QtWidgets import QApplication

        # GUI 모듈 import (실제 실행 X)
        from GUI.staru_main import StarUWindow
        from ui.widgets.backtest.main import BacktestWidget
        from ui.widgets.optimization.main import OptimizationWidget
        from ui.design_system.theme import ThemeGenerator

        return True, "GUI imports successful (PyQt6 ready)"

    except ImportError as e:
        return False, f"GUI import failed: {str(e)}"
    except Exception as e:
        return False, f"GUI check error: {str(e)}"


def main():
    """메인 검증 루틴"""

    print("=" * 70)
    print("TwinStar-Quantum 프로덕션 준비 검증")
    print("=" * 70)
    print()

    # 작업 디렉토리 확인
    if not Path('core').exists() or not Path('exchanges').exists():
        print("[ERROR] Run this script from project root (TwinStar-Quantum/)")
        sys.exit(1)

    checks = [
        ("1. Entry Points", check_entry_points),
        ("2. Import Integrity", check_import_integrity),
        ("3. Config Files", check_config_files),
        ("4. Storage Init", check_storage_init),
        ("5. SSOT Compliance", check_ssot_compliance),
        ("6. GUI Launch", check_gui_launch)
    ]

    results = []

    for check_name, check_func in checks:
        print(f"Checking {check_name}...", end=" ")

        try:
            success, message = check_func()
            results.append(success)

            if success:
                print(f"[OK] PASS")
                print(f"   {message}")
            else:
                print(f"[FAIL] FAIL")
                print(f"   {message}")
        except Exception as e:
            results.append(False)
            print(f"[ERROR] ERROR")
            print(f"   Unexpected error: {str(e)}")

        print()

    # 최종 결과
    passed = sum(results)
    total = len(results)

    print("=" * 70)
    print(f"Results: {passed}/{total} checks passed")
    print("=" * 70)
    print()

    if passed == total:
        print("[SUCCESS] Production Ready! All checks passed.")
        print()
        print("Next steps:")
        print("  1. python run_gui.py")
        print("  2. python web/run_server.py")
        print("  3. Review VS Code Problems tab (Pyright errors)")
        sys.exit(0)
    else:
        print("[WARNING] Production NOT Ready. Fix the issues above.")
        print()
        print("Common fixes:")
        print("  - pip install -r requirements.txt")
        print("  - Create missing config files")
        print("  - Check CLAUDE.md for SSOT guidelines")
        sys.exit(1)


if __name__ == '__main__':
    main()
