@echo off
chcp 65001 > nul
cd /d c:\매매전략

echo ========================================
echo  TwinStar Quantum - Import 검증 테스트
echo ========================================
echo.

echo [1/6] core.strategy_core...
python -c "from core.strategy_core import AlphaX7Core; print('  OK')" 2>&1
if errorlevel 1 echo   FAIL

echo [2/6] core.optimizer...
python -c "from core.optimizer import BacktestOptimizer; print('  OK')" 2>&1
if errorlevel 1 echo   FAIL

echo [3/6] core.unified_bot...
python -c "from core.unified_bot import UnifiedBot; print('  OK')" 2>&1
if errorlevel 1 echo   FAIL

echo [4/6] exchanges.exchange_manager...
python -c "from exchanges.exchange_manager import get_exchange_manager; print('  OK')" 2>&1
if errorlevel 1 echo   FAIL

echo [5/6] storage.secure_storage...
python -c "from storage.secure_storage import get_secure_storage; print('  OK')" 2>&1
if errorlevel 1 echo   FAIL

echo [6/6] utils.preset_manager...
python -c "from utils.preset_manager import get_preset_manager; print('  OK')" 2>&1
if errorlevel 1 echo   FAIL

echo.
echo ========================================
echo  GUI 위젯 Import 테스트
echo ========================================
echo.

echo [1/5] trading_dashboard...
python -c "import sys; sys.path.insert(0,'GUI'); from trading_dashboard import TradingDashboard; print('  OK')" 2>&1

echo [2/5] backtest_widget...
python -c "import sys; sys.path.insert(0,'GUI'); from backtest_widget import BacktestWidget; print('  OK')" 2>&1

echo [3/5] optimization_widget...
python -c "import sys; sys.path.insert(0,'GUI'); from optimization_widget import OptimizationWidget; print('  OK')" 2>&1

echo [4/5] settings_widget...
python -c "import sys; sys.path.insert(0,'GUI'); from settings_widget import SettingsWidget; print('  OK')" 2>&1

echo [5/5] staru_main...
python -c "import sys; sys.path.insert(0,'GUI'); from staru_main import StarUWindow; print('  OK')" 2>&1

echo.
echo ========================================
echo  테스트 완료
echo ========================================
pause
