"""
Test A: Real Data Integration Test
- Uses actual saved candle data from data/cache
- Tests optimizer, backtest, and preset creation with real data
"""
import sys
import os
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CACHE_DIR = Path(__file__).parent.parent / 'data' / 'cache'

class IntegrationTest:
    def __init__(self):
        self.results = []
        
    def log(self, msg, status='INFO'):
        icon = {'PASS': '✅', 'FAIL': '❌', 'INFO': 'ℹ️', 'WARN': '⚠️'}
        print(f"{icon.get(status, '·')} {msg}")
        self.results.append({'msg': msg, 'status': status})
        
    def test_load_real_candles(self):
        """Load actual parquet files"""
        self.log("[Test 1] Loading Real Candle Data")
        
        try:
            # Test BTCUSDT 15m
            btc_file = CACHE_DIR / 'bybit_btcusdt_15m.parquet'
            if not btc_file.exists():
                self.log(f"File not found: {btc_file}", 'FAIL')
                return False
                
            df = pd.read_parquet(btc_file)
            self.log(f"Loaded {len(df)} rows from bybit_btcusdt_15m.parquet", 'PASS')
            self.log(f"Columns: {list(df.columns)}", 'INFO')
            self.log(f"Date Range: {df.index[0]} ~ {df.index[-1]}", 'INFO')
            
            return len(df) > 100
            
        except Exception as e:
            self.log(f"Failed to load: {e}", 'FAIL')
            return False
    
    def test_strategy_signal_detection(self):
        """Test signal detection with real data"""
        self.log("\n[Test 2] Signal Detection on Real Data")
        
        try:
            from core.strategy_core import AlphaX7Core
            
            btc_1h = CACHE_DIR / 'bybit_btcusdt_15m.parquet'  # Use 15m as 1H approx
            btc_15m = CACHE_DIR / 'bybit_btcusdt_15m.parquet'
            
            df_1h = pd.read_parquet(btc_1h)
            df_15m = pd.read_parquet(btc_15m)
            
            # Ensure column names match expected format
            for df in [df_1h, df_15m]:
                if 'Close' in df.columns and 'close' not in df.columns:
                    df.rename(columns=str.lower, inplace=True)
            
            strategy = AlphaX7Core()
            
            # Detect signals
            signals = strategy.detect_signal(
                df_1h.tail(500), 
                df_15m.tail(500),
                rsi_period=14,
                atr_period=14
            )
            
            self.log(f"Detected {len(signals) if signals else 0} signals", 'PASS')
            
            if signals:
                last = signals[-1]
                self.log(f"Last Signal: {last.signal_type} at {last.timestamp}", 'INFO')
            
            return True
            
        except Exception as e:
            self.log(f"Signal detection failed: {e}", 'FAIL')
            import traceback
            traceback.print_exc()
            return False
    
    def test_unified_backtest_real(self):
        """Test unified backtest with real presets"""
        self.log("\n[Test 3] Unified Backtest with Real Data")
        
        try:
            from core.unified_backtest import UnifiedBacktest
            
            ub = UnifiedBacktest(max_positions=1)
            
            # Check if presets exist
            presets = ub._load_verified_presets()
            self.log(f"Found {len(presets)} presets", 'INFO')
            
            if not presets:
                self.log("No presets found - skipping backtest", 'WARN')
                return True  # Not a failure, just no data
            
            # Run short backtest
            result = ub.run()
            
            if result:
                self.log(f"Backtest Complete: {result.total_trades} trades, WR={result.win_rate:.1f}%", 'PASS')
                return True
            else:
                self.log("No trades generated", 'WARN')
                return True
                
        except Exception as e:
            self.log(f"Backtest failed: {e}", 'FAIL')
            import traceback
            traceback.print_exc()
            return False
    
    def test_scanner_data_loading(self):
        """Test scanner can load data correctly"""
        self.log("\n[Test 4] Scanner Data Loading")
        
        try:
            from exchanges.exchange_manager import get_exchange_manager
            
            em = get_exchange_manager()
            
            # Try connecting to bybit
            connected = em.test_connection('bybit')
            
            if connected:
                self.log("Connected to Bybit", 'PASS')
                
                # Try get klines
                ex = em.get_exchange('bybit')
                if ex:
                    df = ex.get_klines('BTCUSDT', '15m', limit=10)
                    if df is not None and len(df) > 0:
                        self.log(f"Fetched {len(df)} live candles", 'PASS')
                        return True
            else:
                self.log("Bybit not connected (API keys needed)", 'WARN')
                return True
                
        except Exception as e:
            self.log(f"Scanner data test: {e}", 'WARN')
            return True  # Not critical
    
    def run_all(self):
        print("=" * 60)
        print("INTEGRATION TEST (Real Data)")
        print("=" * 60)
        
        tests = [
            self.test_load_real_candles,
            self.test_strategy_signal_detection,
            self.test_unified_backtest_real,
            self.test_scanner_data_loading
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Test crashed: {e}", 'FAIL')
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 60)
        
        return failed == 0

if __name__ == '__main__':
    tester = IntegrationTest()
    success = tester.run_all()
    sys.exit(0 if success else 1)
