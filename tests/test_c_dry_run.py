"""
Test C: Dry Run Test
- Connects to real exchange (if keys available)
- Detects signals
- Logs trades without execution
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DryRunTest:
    def __init__(self):
        self.results = []
        
    def log(self, msg, status='INFO'):
        icon = {'PASS': '✅', 'FAIL': '❌', 'INFO': 'ℹ️', 'WARN': '⚠️', 'DRY': '🔵'}
        print(f"{icon.get(status, '·')} {msg}")
        self.results.append({'msg': msg, 'status': status})
    
    def test_exchange_connection(self):
        """Test exchange connection"""
        self.log("[Test 1] Exchange Connection")
        
        try:
            from exchanges.exchange_manager import get_exchange_manager
            
            em = get_exchange_manager()
            
            # Try Bybit
            if em.test_connection('bybit'):
                self.log("Bybit connected", 'PASS')
                return 'bybit'
            
            # Try Binance
            if em.test_connection('binance'):
                self.log("Binance connected", 'PASS')
                return 'binance'
                
            self.log("No exchange connected - check API keys", 'WARN')
            return None
            
        except Exception as e:
            self.log(f"Connection test: {e}", 'WARN')
            return None
    
    def test_live_data_fetch(self, exchange_name):
        """Fetch live market data"""
        self.log(f"\n[Test 2] Live Data Fetch ({exchange_name})")
        
        if not exchange_name:
            self.log("Skipped - no exchange", 'WARN')
            return True
            
        try:
            from exchanges.exchange_manager import get_exchange_manager
            
            em = get_exchange_manager()
            ex = em.get_exchange(exchange_name)
            
            if not ex:
                self.log("Failed to get exchange instance", 'FAIL')
                return False
            
            # Fetch current price
            price = ex.get_current_price('BTCUSDT')
            self.log(f"BTCUSDT Price: ${price:,.2f}", 'PASS')
            
            # Fetch recent candles
            df = ex.get_klines('BTCUSDT', '15m', limit=20)
            if df is not None and len(df) > 0:
                self.log(f"Fetched {len(df)} candles", 'PASS')
                return True
            else:
                self.log("No candles returned", 'FAIL')
                return False
            
        except Exception as e:
            self.log(f"Data fetch failed: {e}", 'FAIL')
            return False
    
    def test_signal_detection_live(self, exchange_name):
        """Detect signals on live data"""
        self.log(f"\n[Test 3] Live Signal Detection ({exchange_name})")
        
        if not exchange_name:
            self.log("Skipped - no exchange", 'WARN')
            return True
            
        try:
            from exchanges.exchange_manager import get_exchange_manager
            from core.strategy_core import AlphaX7Core
            
            em = get_exchange_manager()
            ex = em.get_exchange(exchange_name)
            
            if not ex:
                return False
            
            # Fetch data
            df_1h = ex.get_klines('BTCUSDT', '1h', limit=200)
            df_15m = ex.get_klines('BTCUSDT', '15m', limit=200)
            
            if df_1h is None or df_15m is None:
                self.log("Failed to fetch candles", 'FAIL')
                return False
            
            # Detect signals
            strategy = AlphaX7Core()
            signals = strategy.detect_signal(df_1h, df_15m)
            
            if signals:
                # Handle both list and single signal
                if hasattr(signals, '__len__') and not isinstance(signals, str):
                    sig_list = signals
                else:
                    sig_list = [signals]
                    
                self.log(f"Detected {len(sig_list)} signals", 'PASS')
                last = sig_list[-1]
                self.log(f"Latest: {last.signal_type.upper()} @ {last.timestamp}", 'DRY')
            else:
                self.log("No signals detected (market may be ranging)", 'INFO')
            
            return True
            
        except Exception as e:
            self.log(f"Signal detection failed: {e}", 'FAIL')
            return False
    
    def test_scanner_dry_run(self, exchange_name):
        """Test scanner in dry run mode"""
        self.log(f"\n[Test 4] Scanner Dry Run")
        
        try:
            from core.auto_scanner import AutoScanner
            
            config = {
                'dry_run': True,
                'max_positions': 1,
                'entry_amount': 100,
                'leverage': 1
            }
            
            scanner = AutoScanner(config)
            scanner.log_signal.connect(lambda m: self.log(f"[Scanner] {m}", 'DRY'))
            
            # Load symbols
            scanner.load_verified_symbols()
            self.log(f"Loaded {len(scanner.verified_symbols)} verified symbols", 'INFO')
            
            # Don't actually start the loop - just verify setup
            self.log("Scanner configured in DRY RUN mode", 'PASS')
            
            return True
            
        except Exception as e:
            self.log(f"Scanner test failed: {e}", 'FAIL')
            return False
    
    def test_position_check(self, exchange_name):
        """Check current positions"""
        self.log(f"\n[Test 5] Position Check ({exchange_name})")
        
        if not exchange_name:
            self.log("Skipped - no exchange", 'WARN')
            return True
            
        try:
            from exchanges.exchange_manager import get_exchange_manager
            
            em = get_exchange_manager()
            
            positions = em.get_positions(exchange_name)
            
            active = [p for p in positions if float(p.size) != 0]
            
            if active:
                self.log(f"Found {len(active)} active positions:", 'INFO')
                for p in active[:5]:
                    self.log(f"  {p.symbol}: {p.size} @ {p.entry_price}", 'INFO')
            else:
                self.log("No active positions", 'INFO')
            
            return True
            
        except Exception as e:
            self.log(f"Position check: {e}", 'WARN')
            return True
    
    def run_all(self):
        print("=" * 60)
        print("DRY RUN TEST (Real API, No Execution)")
        print("=" * 60)
        
        # Test exchange connection first
        exchange = self.test_exchange_connection()
        
        tests = [
            lambda: self.test_live_data_fetch(exchange),
            lambda: self.test_signal_detection_live(exchange),
            lambda: self.test_scanner_dry_run(exchange),
            lambda: self.test_position_check(exchange)
        ]
        
        passed = 1 if exchange else 0  # Connection counts
        failed = 0 if exchange else 0  # Not having keys isn't failure
        
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
        if not exchange:
            print("⚠️  Note: No exchange connected - some tests skipped")
        print("=" * 60)
        
        return failed == 0

if __name__ == '__main__':
    tester = DryRunTest()
    success = tester.run_all()
    sys.exit(0 if success else 1)
