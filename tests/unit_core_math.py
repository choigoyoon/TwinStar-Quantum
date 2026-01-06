import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(r"C:\매매전략")))

from core.strategy_core import AlphaX7Core
from utils.indicators import calculate_rsi

class TestCoreMath(unittest.TestCase):
    def setUp(self):
        self.strategy = AlphaX7Core()

    def test_empty_dataframe(self):
        """Test behavior with empty DataFrame"""
        df = pd.DataFrame()
        # Should return None, not crash
        result = self.strategy.detect_signal(df, df)
        self.assertIsNone(result)

    def test_nan_handling_series(self):
        """Test util.indicators.calculate_rsi with NaNs (Series mode)"""
        values = np.random.randn(100)
        # Inject NaNs in middle
        values[50:60] = np.nan
        
        # Test Series calculation
        rsi_series = calculate_rsi(pd.Series(values), period=14, return_series=True)
        
        # Check indices inside NaN region
        # System treats NaN in delta as 0 gain/loss (Safety Feature)
        # So RSI continues to calculate (decaying or changing based on previous averages)
        # We just want to ensure it DOES NOT CRASH and DOES NOT RETURN NaN
        rsi_val = rsi_series.iloc[55]
        self.assertFalse(np.isnan(rsi_val), f"RSI inside NaN block should be valid float, got {rsi_val}")
        
        # Check indices AFTER NaN region
        rsi_val_overlap = rsi_series.iloc[65]
        self.assertFalse(np.isnan(rsi_val_overlap), f"RSI overlapping NaN block should be valid, got {rsi_val_overlap}")
        
        # Check recovery
        valid_idx = 80 # 60 + 14 + buffer
        self.assertFalse(np.isnan(rsi_series.iloc[valid_idx]), f"RSI should recover by index {valid_idx}")

    def test_nan_handling_scalar_strategy(self):
        """Test strategy.calculate_rsi with valid last data"""
        values = np.random.randn(100)
        values[50:60] = np.nan # NaNs far from end
        
        # strategy.calculate_rsi uses numpy array and returns scalar (last value)
        rsi = self.strategy.calculate_rsi(values)
        
        self.assertIsInstance(rsi, float)
        self.assertFalse(np.isnan(rsi), "Scalar RSI should be valid if tail is clean")
        
    def test_detect_signal_short_data(self):
        """Test with insufficient data length"""
        data = {
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='1h'),
            'open': [100]*10, 'high': [105]*10, 'low': [95]*10, 'close': [100]*10, 'volume': [1000]*10
        }
        df = pd.DataFrame(data)
        # Should return None because len < 50
        result = self.strategy.detect_signal(df, df)
        self.assertIsNone(result)

    def test_parameter_injection(self):
        """Test internal parameter injection"""
        df = pd.DataFrame({
             'timestamp': pd.date_range(start='2024-01-01', periods=200, freq='1h'),
             'open': np.random.randn(200) + 100,
             'high': np.random.randn(200) + 105,
             'low': np.random.randn(200) + 95,
             'close': np.random.randn(200) + 100,
             'volume': np.random.randn(200) + 1000
        })
        
        try:
            self.strategy._extract_all_signals(
                df, 
                tolerance=0.05, 
                validity_hours=4, 
                macd_fast=99, 
                macd_slow=100, 
                macd_signal=50
            ) 
        except Exception as e:
            self.fail(f"_extract_all_signals failed with custom params: {e}")

if __name__ == '__main__':
    unittest.main()
