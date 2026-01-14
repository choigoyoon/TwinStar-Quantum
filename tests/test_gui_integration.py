"""
GUI Integration Test - 전체 탭/기능 검증
PyQt5 앱의 주요 컴포넌트 import 및 초기화 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = {}

def test(name, func):
    """테스트 실행 및 결과 기록"""
    try:
        result = func()
        status = "✅" if result else "❌"
        results[name] = result
        print(f"{status} {name}")
        return result
    except Exception as e:
        results[name] = False
        print(f"❌ {name} - Error: {e}")
        return False

# ========================================
# 1. 기본 실행 테스트
# ========================================
def test_basic_imports():
    """기본 모듈 import 테스트"""
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtCore import Qt
    return True

def test_main_window():
    """메인 윈도우 클래스 로드"""
    from GUI.staru_main import StarUWindow
    return hasattr(StarUWindow, '__init__')

# ========================================
# 2. 최적화 탭 테스트
# ========================================
def test_optimization_widget():
    """최적화 위젯 import"""
    from GUI.optimization_widget import OptimizationWidget
    return hasattr(OptimizationWidget, 'start_optimization')

def test_batch_optimizer():
    """배치 옵티마이저 import"""
    from core.batch_optimizer import BatchOptimizer
    bo = BatchOptimizer()
    return hasattr(bo, 'run')

# ========================================
# 3. 백테스트 탭 테스트
# ========================================
def test_backtest_widget():
    """백테스트 위젯 import"""
    from GUI.backtest_widget import BacktestWidget
    return hasattr(BacktestWidget, 'run_backtest')

def test_unified_backtest():
    """통합 백테스트 엔진 import"""
    from core.unified_backtest import UnifiedBacktest
    ub = UnifiedBacktest()
    return hasattr(ub, 'run')

# ========================================
# 4. 자동매매 탭 테스트
# ========================================
def test_auto_pipeline_widget():
    """자동 파이프라인 위젯 import"""
    from GUI.auto_pipeline_widget import AutoPipelineWidget
    return hasattr(AutoPipelineWidget, '__init__')

def test_auto_scanner():
    """자동 스캐너 import"""
    from core.auto_scanner import AutoScanner
    return hasattr(AutoScanner, 'start')

# ========================================
# 5. 매매 탭 테스트
# ========================================
def test_trading_dashboard():
    """트레이딩 대시보드 import"""
    from GUI.trading_dashboard import TradingDashboard
    return hasattr(TradingDashboard, '__init__')

def test_unified_bot():
    """통합 봇 import"""
    from core.unified_bot import UnifiedBot
    return hasattr(UnifiedBot, 'run')

# ========================================
# 6. 설정 탭 테스트
# ========================================
def test_settings_widget():
    """설정 위젯 import"""
    from GUI.settings_widget import SettingsWidget
    return hasattr(SettingsWidget, '__init__')

def test_config_parameters():
    """설정 파라미터 import"""
    from config.parameters import DEFAULT_PARAMS, SLIPPAGE, FEE
    return 'slippage' in DEFAULT_PARAMS and SLIPPAGE == 0.0006

# ========================================
# 7. 공용 컴포넌트 테스트
# ========================================
def test_exchange_manager():
    """거래소 매니저 import"""
    from exchanges.exchange_manager import ExchangeManager
    return hasattr(ExchangeManager, 'get_exchange')

def test_preset_manager():
    """프리셋 매니저 import"""
    from utils.preset_manager import get_preset_manager
    pm = get_preset_manager()
    return hasattr(pm, 'load_preset')

def test_paths():
    """경로 관리 import"""
    from paths import Paths
    return hasattr(Paths, 'CACHE') and hasattr(Paths, 'PRESETS')


def main():
    print("=" * 60)
    print("GUI 통합 테스트")
    print("=" * 60)
    
    # 1. 기본 실행
    print("\n[1. 기본 실행]")
    test("PyQt5 Import", test_basic_imports)
    test("MainWindow Class", test_main_window)
    
    # 2. 최적화 탭
    print("\n[2. 최적화 탭]")
    test("OptimizationWidget", test_optimization_widget)
    test("BatchOptimizer", test_batch_optimizer)
    
    # 3. 백테스트 탭
    print("\n[3. 백테스트 탭]")
    test("BacktestWidget", test_backtest_widget)
    test("UnifiedBacktest", test_unified_backtest)
    
    # 4. 자동매매 탭
    print("\n[4. 자동매매 탭]")
    test("AutoPipelineWidget", test_auto_pipeline_widget)
    test("AutoScanner", test_auto_scanner)
    
    # 5. 매매 탭
    print("\n[5. 매매 탭]")
    test("TradingDashboard", test_trading_dashboard)
    test("UnifiedBot", test_unified_bot)
    
    # 6. 설정 탭
    print("\n[6. 설정 탭]")
    test("SettingsWidget", test_settings_widget)
    test("ConfigParameters", test_config_parameters)
    
    # 7. 공용 컴포넌트
    print("\n[7. 공용 컴포넌트]")
    test("ExchangeManager", test_exchange_manager)
    test("PresetManager", test_preset_manager)
    test("Paths", test_paths)
    
    # 결과 요약
    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"총 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 GUI 통합 테스트 전부 통과!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"❌ 실패 항목: {', '.join(failed)}")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
