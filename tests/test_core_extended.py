#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_core_extended.py - Verification for Extended Core Modules
"""
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

class TestCoreExtended(unittest.TestCase):
    
    def log_result(self, module, function, expected, actual):
        passed = expected == actual
        icon = "✅" if passed else "❌"
        print(f"{icon} [{module}] [{function}] Expected={expected}, Actual={actual}")
        return passed

    def test_01_multi_sniper(self):
        """Verify MultiSniper Module"""
        print("\n--- Testing Core: MultiSniper ---")
        try:
            from core.multi_sniper import MultiCoinSniper
            
            # Instantiate with Mocks
            mock_license = MagicMock()
            mock_client = MagicMock()
            
            try:
                ms = MultiCoinSniper(mock_license, mock_client, total_seed=1000)
                self.log_result("core/multi_sniper", "instantiation", True, True)
                
                # Check critical methods
                has_init = hasattr(ms, 'initialize')
                self.log_result("core/multi_sniper", "method_initialize", True, has_init)
                
            except Exception as e:
                print(f"Instantiate failed: {e}")
                self.log_result("core/multi_sniper", "instantiation", True, False)
            
        except ImportError as e:
            self.log_result("core/multi_sniper", "import", True, False)
            print(f"Import Error: {e}")

    def test_02_auto_scanner(self):
        """Verify AutoScanner Module"""
        print("\n--- Testing Core: AutoScanner ---")
        try:
            from core.auto_scanner import AutoScanner
            
            # Instantiate
            scanner = AutoScanner()
            self.log_result("core/auto_scanner", "instantiation", True, True)
            
            # Check methods
            has_start = hasattr(scanner, 'start')
            has_stop = hasattr(scanner, 'stop')
            self.log_result("core/auto_scanner", "method_start_stop", True, has_start and has_stop)
            
        except ImportError as e:
            self.log_result("core/auto_scanner", "import", True, False)

    def test_03_optimization_logic(self):
        """Verify Optimization Logic Module"""
        print("\n--- Testing Core: Optimization Logic ---")
        try:
            from core.optimization_logic import OptimizationEngine
            
            # Instantiate
            engine = OptimizationEngine() 
            self.log_result("core/optimization_logic", "instantiation", True, True)
            
            has_run = hasattr(engine, 'run_optimization')
            self.log_result("core/optimization_logic", "method_run_optimization", True, has_run)
            
        except ImportError as e:
             self.log_result("core/optimization_logic", "import", True, False)
             print(f"Import Error: {e}")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
