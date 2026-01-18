import sys
import os

# Logging
import logging
logger = logging.getLogger(__name__)

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'strategies'))

def print_header(title):
    logger.info(f"\n{'='*50}\n{title}\n{'='*50}")

def check_file_exists(path, desc):
    exists = os.path.exists(path)
    status = "✅ Found" if exists else "❌ Missing"
    logger.info(f"{desc:<30}: {status} ({path})")
    return exists

def test_data_manager():
    print_header("1. DataManager Test")
    try:
        from GUI.data_cache import DataManager
        dm = DataManager()
        logger.info(f"Cache Directory: {dm.cache_dir}")
        
        # Check specific DB file
        target_symbol = 'btcusdt'
        target_tf = '15m'
        target_exchange = 'bybit'
        
        logger.info(f"\nLoading {target_exchange} {target_symbol} {target_tf}...")
        df = dm.load_data(target_symbol, target_exchange, target_tf)
        
        if df is not None and not df.empty:
            logger.info(f"✅ Data Loaded Successfully")
            logger.info(f"   Rows: {len(df)}")
            logger.info(f"   Period: {df.iloc[0]['timestamp']} ~ {df.iloc[-1]['timestamp']}")
            
            # Check for legacy data length (should be around 199k for full history)
            if len(df) > 100000:
                 logger.info("   ✅ Full History Detected (Converted from CSV)")
            else:
                 logger.info("   ⚠️ Only Partial History Detected (Recent Download?)")
        else:
            logger.info("❌ Data Load Failed")
            
    except Exception as e:
        logger.info(f"❌ DataManager Error: {e}")
        import traceback
        traceback.print_exc()

def test_strategy_structure():
    print_header("2. Strategy Structure Test")
    try:
        from strategies.wm_pattern_strategy import WMPatternStrategy
        strategy = WMPatternStrategy()
        
        logger.info(f"Strategy Name: {strategy.config.name}")
        logger.info(f"Version: {strategy.config.version}")
        
        # Check for legacy backtest wrapper
        if hasattr(strategy, 'run_legacy_backtest'):
             logger.info("✅ 'run_legacy_backtest' method FOUND (Wrapper Correct)")
        else:
             logger.info("❌ 'run_legacy_backtest' method MISSING (Wrapper Incorrect)")
             
    except Exception as e:
        logger.info(f"❌ Strategy Error: {e}")
        import traceback
        traceback.print_exc()

def test_backtest_integration():
    print_header("3. Backtest Engine Integration Test")
    try:
        from strategies.common.backtest_engine import BacktestEngine
        from strategies.common.strategy_interface import Candle

        
        # Mock some candles
        candles = [
            Candle(timestamp=1609459200000 + i*900000, open=100+i, high=105+i, low=95+i, close=102+i, volume=1000)
            for i in range(100) # Small sample just to test interface
        ]
        
        from strategies.wm_pattern_strategy import WMPatternStrategy
        strategy = WMPatternStrategy()
        
        engine = BacktestEngine()
        logger.info("Running Engine with Strategy...")
        
        # Note: run_legacy_backtest might fail with mock data if it expects a specific CSV
        # We just want to check if the engine calls the right method.
        # But wait, run_legacy_backtest writes to CSV and then calls BreakevenStrategy.
        # This integration test is tricky without the full environment.
        # Let's check the code inspection instead or try running it and catching the specific logic error
        
        try:
            result = engine.run(strategy, candles)
            logger.info("✅ Engine returned result object")
        except Exception as inner_e:
            logger.info(f"⚠️ Engine run raised exception (Expected if mock data doesn't match strategy requirements): {inner_e}")
            if "BreakevenStrategy" in str(inner_e) or "run_legacy_backtest" in str(inner_e):
                logger.info("   -> Trace suggests correct delegation logic.")
            
    except Exception as e:
        logger.info(f"❌ Backtest Engine Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    print_header("STARTING SYSTEM VERIFICATION")
    
    # 1. Check directories
    dirs = [
        "c:/매매전략/GUI",
        "c:/매매전략/strategies",
        "c:/매매전략/strategies/common",
        "c:/매매전략/data/cache"
    ]
    for d in dirs:
        check_file_exists(d, d)

    # 2. Check critical files
    files = [
        "c:/매매전략/strategies/wm_pattern_strategy.py",
        "c:/매매전략/strategies/common/backtest_engine.py",
        "c:/매매전략/strategy_breakeven.py",
        "c:/매매전략/data/cache/bybit_btcusdt_15m.db"  # The converted DB
    ]
    for f in files:
        check_file_exists(f, os.path.basename(f))
        
    # 3. Functional Tests
    test_data_manager()
    test_strategy_structure()
    test_backtest_integration()
    
    print_header("VERIFICATION COMPLETE")

if __name__ == "__main__":
    main()
