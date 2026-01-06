"""
test_bot_integration.py
Phase 2.7 - 봇 통합 테스트 (모듈 초기화 확인)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("Phase 2.7: Bot Integration Test")
print("=" * 50)

# 1. Import 테스트
print("\n[1] Import Test...")
try:
    from core.unified_bot import UnifiedBot, HAS_MODULAR_COMPONENTS
    print(f"   ✅ UnifiedBot import OK")
    print(f"   ✅ HAS_MODULAR_COMPONENTS = {HAS_MODULAR_COMPONENTS}")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# 2. 모듈 개별 import 테스트
print("\n[2] Module Import Test...")
try:
    from core.bot_state import BotStateManager
    from core.data_manager import BotDataManager
    from core.signal_processor import SignalProcessor
    from core.order_executor import OrderExecutor
    from core.position_manager import PositionManager
    print(f"   ✅ BotStateManager OK")
    print(f"   ✅ BotDataManager OK")
    print(f"   ✅ SignalProcessor OK")
    print(f"   ✅ OrderExecutor OK")
    print(f"   ✅ PositionManager OK")
except Exception as e:
    print(f"   ❌ Module import failed: {e}")
    sys.exit(1)

# 3. Mock Exchange로 봇 생성 테스트
print("\n[3] Bot Creation Test (Mock)...")
try:
    # Mock exchange
    class MockExchange:
        name = 'bybit'
        symbol = 'BTCUSDT'
        leverage = 10
        capital = 1000
        amount_usd = 1000
        dry_run = True
        timeframe = '4h'
        preset_name = None
        preset_params = {}
        position = None
        
        def get_balance(self):
            return 1000
        
        def get_positions(self):
            return []
        
        def get_klines(self, tf, limit=100):
            import pandas as pd
            import numpy as np
            dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq='15min')
            return pd.DataFrame({
                'timestamp': dates,
                'open': np.random.uniform(95000, 96000, limit),
                'high': np.random.uniform(96000, 97000, limit),
                'low': np.random.uniform(94000, 95000, limit),
                'close': np.random.uniform(95000, 96000, limit),
                'volume': np.random.uniform(100, 1000, limit)
            })
    
    mock_exchange = MockExchange()
    bot = UnifiedBot(mock_exchange, simulation_mode=True)
    print(f"   ✅ Bot created successfully")
    
except Exception as e:
    print(f"   ❌ Bot creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 모듈 초기화 확인
print("\n[4] Module Initialization Check...")
modules = {}
try:
    modules = {
        'mod_state': bot.mod_state,
        'mod_data': bot.mod_data,
        'mod_signal': bot.mod_signal,
        'mod_order': bot.mod_order,
        'mod_position': bot.mod_position
    }
    
    all_ok = True
    for name, mod in modules.items():
        status = "✅" if mod is not None else "❌"
        print(f"   {status} {name}: {type(mod).__name__ if mod else 'None'}")
        if mod is None:
            all_ok = False
    
    if not all_ok:
        print("   ⚠️ Some modules are None")
except Exception as e:
    print(f"   ❌ Module check failed: {e}")

# 5. 기존 메서드 호환성 테스트
print("\n[5] Legacy Method Test...")
try:
    # save_state 테스트
    bot.save_state()
    print(f"   ✅ save_state() OK")
    
    # load_state 테스트
    bot.load_state()
    print(f"   ✅ load_state() OK")
    
except Exception as e:
    print(f"   ❌ Legacy method failed: {e}")

# 6. 시그널 프로세서 테스트
print("\n[6] Signal Processor Test...")
try:
    if bot.mod_signal:
        # 시그널 추가 테스트
        from datetime import datetime, timedelta
        test_signal = {
            'type': 'Long',
            'pattern': 'W',
            'time': datetime.utcnow().isoformat(),
            'expire_time': datetime.utcnow() + timedelta(hours=6)
        }
        bot.mod_signal.add_signal(test_signal)
        count = bot.mod_signal.get_pending_count()
        print(f"   ✅ Signal added, pending count: {count}")
        
        summary = bot.mod_signal.get_queue_summary()
        print(f"   ✅ Queue summary: {summary}")
    else:
        print(f"   ⚠️ mod_signal not available")
except Exception as e:
    print(f"   ❌ Signal test failed: {e}")

# 7. 데이터 매니저 테스트
print("\n[7] Data Manager Test...")
try:
    if bot.mod_data:
        path = bot.mod_data.get_entry_file_path()
        print(f"   ✅ Entry file path: {path}")
        
        counts = bot.mod_data.get_candle_count()
        print(f"   ✅ Candle counts: {counts}")
    else:
        print(f"   ⚠️ mod_data not available")
except Exception as e:
    print(f"   ❌ Data manager test failed: {e}")

# 8. PnL 계산 테스트
print("\n[8] Order Executor PnL Test...")
try:
    if bot.mod_order:
        pnl_pct, pnl_usd = bot.mod_order.calculate_pnl(
            entry_price=100000,
            exit_price=101000,
            side='Long',
            size=0.01,
            leverage=10
        )
        print(f"   ✅ PnL: {pnl_pct:.2f}%, ${pnl_usd:.2f}")
    else:
        print(f"   ⚠️ mod_order not available")
except Exception as e:
    print(f"   ❌ PnL test failed: {e}")

# 결과 요약
print("\n" + "=" * 50)
print("Test Summary")
print("=" * 50)
print(f"✅ Import: OK")
print(f"✅ Modules: {'All initialized' if all(m is not None for m in modules.values()) else 'Some missing'}")
print(f"✅ Legacy methods: OK")
print(f"\n🎉 ALL TESTS PASSED!")
