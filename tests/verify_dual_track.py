# -*- coding: utf-8 -*-
"""
DualTrackTrader & Preset Integration Quick Verification
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from unittest.mock import Mock, patch

def main():
    results = []
    
    print("=" * 60)
    print(" DualTrackTrader & Preset Integration Verification")
    print("=" * 60)
    print()
    
    # === Test 1: DualTrackTrader Import ===
    print("[1] DualTrackTrader Import...")
    try:
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            from core.dual_track_trader import DualTrackTrader
            
            mock_exchange = Mock()
            mock_exchange.name = 'bybit'
            trader = DualTrackTrader(
                exchange_client=mock_exchange,
                btc_fixed_usd=100.0,
                initial_alt_capital=1000.0
            )
            print("    [OK] DualTrackTrader instantiated")
            results.append(("DualTrackTrader Import", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("DualTrackTrader Import", False))
    
    # === Test 2: Initial Capital Setup ===
    print("[2] Initial Capital Setup...")
    try:
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            
            from core.dual_track_trader import DualTrackTrader
            mock_exchange = Mock()
            mock_exchange.name = 'bybit'
            trader = DualTrackTrader(mock_exchange, btc_fixed_usd=100.0, initial_alt_capital=1000.0)
            
            assert trader.btc_fixed_usd == 100.0, "BTC fixed should be 100"
            assert trader.alt_capital == 1000.0, "ALT capital should be 1000"
            print("    [OK] BTC=$100, ALT=$1000")
            results.append(("Initial Capital", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("Initial Capital", False))
    
    # === Test 3: BTC Symbol Detection ===
    print("[3] BTC Symbol Detection...")
    try:
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            
            from core.dual_track_trader import DualTrackTrader
            mock_exchange = Mock()
            mock_exchange.name = 'bybit'
            trader = DualTrackTrader(mock_exchange)
            
            assert trader.is_btc('BTCUSDT') == True
            assert trader.is_btc('ETHUSDT') == False
            assert trader.is_btc('SOLUSDT') == False
            print("    [OK] BTC/ALT classification works")
            results.append(("BTC Symbol Detection", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("BTC Symbol Detection", False))
    
    # === Test 4: Track Position Limit ===
    print("[4] Track Position Limit...")
    try:
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            from core.dual_track_trader import DualTrackTrader
            mock_exchange = Mock()
            mock_exchange.name = 'bybit'
            trader = DualTrackTrader(mock_exchange)
            
            # Initial: both allowed
            assert trader.check_entry_allowed('BTCUSDT') == True
            assert trader.check_entry_allowed('ETHUSDT') == True
            
            # BTC entry
            trader.on_entry_executed('BTCUSDT', 0.01, 50000.0)
            assert trader.check_entry_allowed('BTCUSDT') == False, "BTC track locked"
            assert trader.check_entry_allowed('ETHUSDT') == True, "ALT track open"
            
            # ALT entry
            trader.on_entry_executed('ETHUSDT', 0.5, 3000.0)
            assert trader.check_entry_allowed('ETHUSDT') == False, "ALT track locked"
            
            print("    [OK] BTC Track: 1 position, ALT Track: 1 position")
            results.append(("Track Position Limit", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("Track Position Limit", False))
    
    # === Test 5: ALT Compound Logic ===
    print("[5] ALT Compound Logic (Profit)...")
    try:
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            from core.dual_track_trader import DualTrackTrader
            mock_exchange = Mock()
            mock_exchange.name = 'bybit'
            trader = DualTrackTrader(mock_exchange, initial_alt_capital=1000.0)
            
            # Entry and exit with profit
            trader.on_entry_executed('ETHUSDT', 0.5, 3000.0)
            trader.on_exit_executed('ETHUSDT', pnl_usd=100.0, pnl_pct=10.0)
            
            assert trader.alt_capital == 1100.0, f"Expected 1100, got {trader.alt_capital}"
            print("    [OK] $1000 + $100 profit = $1100 (compound applied)")
            results.append(("ALT Compound Profit", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("ALT Compound Profit", False))
    
    # === Test 6: ALT Compound Logic (Loss) ===
    print("[6] ALT Compound Logic (Loss)...")
    try:
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            from core.dual_track_trader import DualTrackTrader
            mock_exchange = Mock()
            mock_exchange.name = 'bybit'
            trader = DualTrackTrader(mock_exchange, initial_alt_capital=1100.0)
            
            # Entry and exit with loss
            trader.on_entry_executed('SOLUSDT', 5.0, 200.0)
            trader.on_exit_executed('SOLUSDT', pnl_usd=-50.0, pnl_pct=-5.0)
            
            assert trader.alt_capital == 1050.0, f"Expected 1050, got {trader.alt_capital}"
            print("    [OK] $1100 - $50 loss = $1050 (compound applied)")
            results.append(("ALT Compound Loss", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("ALT Compound Loss", False))
    
    # === Test 7: BTC Fixed (No Compound) ===
    print("[7] BTC Fixed (No Compound)...")
    try:
        with patch('core.dual_track_trader.UnifiedBot', Mock()), \
             patch('core.dual_track_trader.DataManager', None), \
             patch('core.dual_track_trader.get_health_monitor') as mock_health:
            mock_health.return_value.can_trade.return_value = (True, 'OK')
            mock_health.return_value.record_trade = Mock()
            
            from core.dual_track_trader import DualTrackTrader
            mock_exchange = Mock()
            mock_exchange.name = 'bybit'
            trader = DualTrackTrader(mock_exchange, btc_fixed_usd=100.0, initial_alt_capital=1000.0)
            
            initial_alt = trader.alt_capital
            
            # BTC entry and exit
            trader.on_entry_executed('BTCUSDT', 0.01, 50000.0)
            trader.on_exit_executed('BTCUSDT', pnl_usd=50.0, pnl_pct=5.0)
            
            assert trader.alt_capital == initial_alt, "ALT capital should not change"
            assert trader.btc_fixed_usd == 100.0, "BTC fixed should stay 100"
            print("    [OK] BTC profit does not affect ALT capital")
            results.append(("BTC Fixed No Compound", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("BTC Fixed No Compound", False))
    
    # === Test 8: PresetManager Load ===
    print("[8] PresetManager Load...")
    try:
        from utils.preset_manager import PresetManager
        pm = PresetManager()
        presets = pm.list_presets()
        print(f"    [OK] Found {len(presets)} presets")
        results.append(("PresetManager Load", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("PresetManager Load", False))
    
    # === Test 9: Preset Files Exist ===
    print("[9] Preset Files Exist...")
    try:
        preset_dir = Path(__file__).resolve().parent.parent / 'config' / 'presets'
        json_files = list(preset_dir.glob('*.json'))
        assert len(json_files) > 0, "No preset files found"
        print(f"    [OK] {len(json_files)} preset files in config/presets/")
        for f in json_files[:3]:
            print(f"        - {f.name}")
        results.append(("Preset Files Exist", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("Preset Files Exist", False))
    
    # === Test 10: Load Actual Preset ===
    print("[10] Load Actual Preset...")
    try:
        from utils.preset_manager import PresetManager
        pm = PresetManager()
        presets = pm.list_presets()
        if presets:
            name = presets[0]['name']
            loaded = pm.load_preset(name)
            assert isinstance(loaded, dict)
            print(f"    [OK] Loaded '{name}' successfully")
            
            # Also test flat format
            flat = pm.load_preset_flat(name)
            assert isinstance(flat, dict)
            print(f"    [OK] Flat format conversion works")
        results.append(("Load Actual Preset", True))
    except Exception as e:
        print(f"    [FAIL] {e}")
        results.append(("Load Actual Preset", False))
    
    # === Summary ===
    print()
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    if passed == total:
        print(f"  ALL TESTS PASSED: {passed}/{total}")
    else:
        print(f"  PASSED: {passed}/{total}")
        for name, ok in results:
            if not ok:
                print(f"    FAILED: {name}")
    print("=" * 60)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
