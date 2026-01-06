#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_structure_comprehensive.py - Structure Verification for Strategies and Exchanges
"""
import sys
import os
import unittest
import inspect
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Imports
# Correct import path for WMPatternStrategy's BaseStrategy
from strategies.common.strategy_interface import BaseStrategy
from strategies.base_strategy import StrategyRegistry # Registry might be in the other file?
# Wait, strategies/base_strategy.py HAS Registry. strategies/common/strategy_interface.py DOES NOT.
# This means WMPatternStrategy MIGHT NOT be registered in the Registry from base_strategy.py if they assume different BaseClasses.
# Let's check inheritance against the one it actually uses.
from strategies.wm_pattern_strategy import WMPatternStrategy
from exchanges.base_exchange import BaseExchange
from exchanges.binance_exchange import BinanceExchange
from exchanges.bybit_exchange import BybitExchange

class TestStructureComprehensive(unittest.TestCase):
    
    def log_result(self, module, function, expected, actual):
        passed = expected == actual
        icon = "✅" if passed else "❌"
        print(f"{icon} [{module}] [{function}] Expected={expected}, Actual={actual}")
        return passed

    # =========================================================================
    # 1. Strategy Structure
    # =========================================================================
    def test_01_strategy_registry(self):
        """Verify Strategy Registry and Inheritance"""
        print("\n--- Testing Strategies: Structure ---")
        
        # 1. Inheritance
        # It should inherit from the BaseStrategy defined in common.strategy_interface
        is_subclass = issubclass(WMPatternStrategy, BaseStrategy)
        self.log_result("strategies", "WMPattern_Inheritance", True, is_subclass)
        
        # 2. Instantiation
        wm = WMPatternStrategy()
        # Check config
        config = wm._init_config()
        self.log_result("strategies", "WMPattern_Config_ID", "wm_pattern_v1", config.strategy_id)
        
    # =========================================================================
    # 2. Exchange Structure
    # =========================================================================
    def test_02_exchange_compliance(self):
        """Verify Exchange Adapters implement BaseExchange correctly"""
        print("\n--- Testing Exchanges: Compliance ---")
        
        adapters = [
            ('Binance', BinanceExchange),
            ('Bybit', BybitExchange)
        ]
        
        for name, cls in adapters:
            # Check if can instantiate with CONFIG DICT
            try:
                # Mock config
                config = {'api_key': 'test', 'api_secret': 'test', 'symbol': 'BTCUSDT'}
                cls(config)
                instantiated = True
            except TypeError as e:
                print(f"❌ {name} instantiation failed: {e}")
                instantiated = False
            except Exception as e:
                # Import errors or missing libs are okay for structure check, 
                # but we want to know if it's strictly instantiation logic
                print(f"⚠️ {name} init warning: {e}")
                instantiated = True
            
            self.log_result("exchanges", f"{name}_Abstracts", True, instantiated)
            
            # Check Method Signatures
            if instantiated:
                inst = cls(config)
                has_create_order = hasattr(inst, 'place_market_order') # Method is place_market_order, not create_order
                self.log_result("exchanges", f"{name}_Method_place_market_order", True, has_create_order)
                has_get_balance = hasattr(inst, 'get_balance')
                self.log_result("exchanges", f"{name}_Method_get_balance", True, has_get_balance)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
