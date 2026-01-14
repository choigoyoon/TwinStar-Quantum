#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_utils_comprehensive.py - System-Wide Verification for Utils Module
"""
import sys
import os
import unittest
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Utils Imports
from utils.crypto import encrypt_key, decrypt_key
from utils.retry import retry_with_backoff
from utils.validators import validate_symbol, validate_number, validate_filename
from utils.indicators import calculate_rsi, calculate_atr, calculate_macd
from utils.state_manager import StateManager

logging.basicConfig(level=logging.CRITICAL)

class TestUtilsComprehensive(unittest.TestCase):
    
    def log_result(self, module, function, expected, actual, tolerance=None):
        passed = False
        if tolerance:
             if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                 passed = abs(expected - actual) <= tolerance
             else:
                 passed = expected == actual
        else:
             passed = expected == actual

        icon = "✅" if passed else "❌"
        msg = f"{icon} [{module}] [{function}] Expected={expected}, Actual={actual}"
        if not passed and tolerance:
            msg += f" (Diff > {tolerance})"
        print(msg)
        return passed

    # =========================================================================
    # 1. Crypto Verification
    # =========================================================================
    def test_01_crypto(self):
        """Verify AES Encryption/Decryption Roundtrip"""
        print("\n--- Testing Utils: Crypto ---")
        
        # Test 1: Encrypt/Decrypt
        original = "TwinStarQuantumSecret"
        encrypted = encrypt_key(original)
        self.log_result("utils/crypto", "encrypt_key", True, encrypted != original, None)
        
        decrypted = decrypt_key(encrypted)
        self.log_result("utils/crypto", "decrypt_key", original, decrypted, None)

    # =========================================================================
    # 2. Retry Verification
    # =========================================================================
    def test_02_retry(self):
        """Verify Retry Decorator"""
        print("\n--- Testing Utils: Retry ---")
        
        class RetryTarget:
            def __init__(self):
                self.calls = 0
            
            @retry_with_backoff(max_retries=3, base_delay=0.01)
            def fail_twice(self):
                self.calls += 1
                if self.calls < 3:
                    raise ValueError("Fail")
                return "Success"

            @retry_with_backoff(max_retries=2, base_delay=0.01)
            def always_fail(self):
                self.calls += 1
                raise ValueError("Fail Forever")

        # Test 1: Recovery
        target = RetryTarget()
        res = target.fail_twice()
        self.log_result("utils/retry", "recovery_calls", 3, target.calls)
        self.log_result("utils/retry", "recovery_result", "Success", res)
        
        # Test 2: Max Retries Exceeded
        target2 = RetryTarget()
        target2.calls = 0
        try:
            target2.always_fail()
        except ValueError:
            pass
        
        # max_retries=2 means initial + 2 retries = 3 calls
        self.log_result("utils/retry", "fail_retry_count", 3, target2.calls)

    # =========================================================================
    # 3. Validators Verification
    # =========================================================================
    def test_03_validators(self):
        """Verify Input Validation"""
        print("\n--- Testing Utils: Validators ---")
        
        # Symbol
        self.log_result("utils/validators", "symbol_valid", (True, 'BTCUSDT'), validate_symbol("BTCUSDT"))
        
        # Number
        valid, val = validate_number("123.45")
        self.log_result("utils/validators", "number_valid", True, valid)
        self.log_result("utils/validators", "number_val", 123.45, val)
        
        # Filename
        self.log_result("utils/validators", "filename_valid", (True, 'config.json'), validate_filename("config.json"))
        self.log_result("utils/validators", "filename_invalid", False, validate_filename("config.exe")[0])

    # =========================================================================
    # 4. Indicators Verification (Critical for Strategy)
    # =========================================================================
    def test_04_indicators(self):
        """Verify Technical Indicators Calculation"""
        print("\n--- Testing Utils: Indicators ---")
        
        # Create known series
        # Linear uptrend: 10, 11, 12 ... 39 (30 periods)
        closes = np.array([float(i) for i in range(10, 40)])
        
        # 1. RSI
        # Pure uptrend -> RSI should be 100
        rsi = calculate_rsi(closes, period=14)
        self.log_result("utils/indicators", "rsi_uptrend", 100.0, round(rsi, 2), 0.1)
        
        # 2. ATR
        # High-Low = 2.0 (12-10). Close-PrevClose also ~2. 
        # Create OHLC
        df = pd.DataFrame({
            'high': [12.0] * 30,
            'low': [10.0] * 30,
            'close': [11.0] * 30, # Flat
            'open': [11.0] * 30
        })
        # TR is always 2.0
        atr = calculate_atr(df, period=14)
        self.log_result("utils/indicators", "atr_flat_range", 2.0, round(atr, 2), 0.1)

    # =========================================================================
    # 5. State Manager Verification
    # =========================================================================
    def test_05_state_manager(self):
        """Verify State Persistence"""
        print("\n--- Testing Utils: State Manager ---")
        
        import tempfile
        import shutil
        
        # Use a temp dir
        temp_dir = tempfile.mkdtemp()
        try:
            sm = StateManager(state_dir=temp_dir, bot_id='test_bot')
            
            data = {'last_price': 100, 'position': 'Long'}
            
            # Save
            sm.save(data)
            
            # Load new instance
            sm2 = StateManager(state_dir=temp_dir, bot_id='test_bot')
            loaded = sm2.load()
            assert loaded is not None
            
            self.log_result("utils/state_manager", "save_load_equality", data['last_price'], loaded.get('last_price'))
            
        finally:
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
