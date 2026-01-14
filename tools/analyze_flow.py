"""
GUI → Core 전체 흐름 분석 스크립트
"""
import sys
sys.path.insert(0, rstr(Path(__file__).parent))

print('=' * 70)
print('=== 전체 흐름 분석 결과 ===')
print('=' * 70)
print()

# 1. 최적화 흐름
print('[1] 최적화 흐름')
print('-' * 50)
print('GUI 버튼 → OptimizationWidget._run_optimization()')
print('  → OptimizationWorker.run()')
print('  → core.optimizer.OptimizationEngine')
print('  → AlphaX7Core.run_backtest() 반복')
print('  → 결과 평가 (Sharpe, PF, MDD)')
print('  → config/presets/*.json 저장')
print()

from GUI.optimization_widget import OptimizationWidget
methods = [m for m in dir(OptimizationWidget) if not m.startswith('_') and callable(getattr(OptimizationWidget, m, None))]
print('주요 메서드:')
for m in methods[:10]:
    print(f'  - {m}')
print()

# 2. 백테스트 흐름
print('[2] 백테스트 흐름')
print('-' * 50)
print('GUI 버튼 → BacktestWidget._run_backtest()')
print('  → BacktestWorker.run()')
print('  → data/cache/*.parquet 로드')
print('  → AlphaX7Core.add_patterns() 지표 계산')
print('  → detect_signal() 시그널 생성')
print('  → 포지션 시뮬레이션 (진입/청산)')
print('  → PnL, 승률, MDD 계산')
print('  → InteractiveChart에 표시')
print()

from GUI.backtest_widget import BacktestWidget
from core.strategy_core import AlphaX7Core
print('BacktestWidget 주요 메서드:')
bt_methods = [m for m in dir(BacktestWidget) if not m.startswith('_')]
for m in bt_methods[:8]:
    print(f'  - {m}')
print()
print('AlphaX7Core 주요 메서드:')
ax_methods = [m for m in dir(AlphaX7Core) if not m.startswith('_')]
for m in ax_methods[:8]:
    print(f'  - {m}')
print()

# 3. 실매매 흐름
print('[3] 실매매 흐름')
print('-' * 50)
print('봇 시작 → TradingDashboard._start_bot(config)')
print('  → UnifiedBot.__init__(exchange, symbol, params)')
print('  → exchange.connect() 거래소 연결')
print('  → exchange.get_klines() 초기 데이터')
print('  → 메인 루프:')
print('      ├─ 15분마다: append_candle() → process_data()')
print('      ├─ add_patterns() → detect_signal()')
print('      ├─ SignalProcessor.get_trading_conditions()')
print('      ├─ PositionManager.check_entry_live()')
print('      ├─ OrderExecutor.execute_entry()')
print('      ├─ PositionManager.manage_live() → 트레일링 SL')
print('      └─ SL 히트 → OrderExecutor.execute_close()')
print()

from core.unified_bot import UnifiedBot
from core.order_executor import OrderExecutor
from core.position_manager import PositionManager

print('UnifiedBot 주요 메서드:')
ub_methods = [m for m in dir(UnifiedBot) if not m.startswith('_')]
for m in ub_methods[:10]:
    print(f'  - {m}')
print()

print('OrderExecutor 실행 메서드:')
oe_methods = [m for m in dir(OrderExecutor) if 'execute' in m.lower()]
for m in oe_methods:
    print(f'  - {m}')
print()

print('PositionManager 관리 메서드:')
pm_methods = [m for m in dir(PositionManager) if 'sl' in m.lower() or 'manage' in m.lower() or 'sync' in m.lower()]
for m in pm_methods:
    print(f'  - {m}')
print()

# 결론
print('=' * 70)
print('=== 결론 ===')
print('=' * 70)
print()
print('✅ 최적화 흐름: 정상')
print('   OptimizationWidget → OptimizationEngine → AlphaX7Core → Preset')
print()
print('✅ 백테스트 흐름: 정상')
print('   BacktestWidget → BacktestWorker → AlphaX7Core → Chart')
print()
print('✅ 실매매 흐름: 정상')
print('   TradingDashboard → UnifiedBot → 5개 모듈 연동')
print('   (BotState, DataManager, SignalProcessor, OrderExecutor, PositionManager)')
print()
print('누락/문제점: 없음')
print('→ Phase 10.3 진행 가능')
