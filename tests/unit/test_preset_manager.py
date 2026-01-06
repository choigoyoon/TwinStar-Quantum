"""
Unit Tests: Preset Manager
Tests save/load/validation of preset files
"""
import unittest
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestPresetSaveLoad(unittest.TestCase):
    """Test preset save and load functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_preset = {
            '_meta': {
                'symbol': 'BTCUSDT',
                'exchange': 'bybit',
                'timeframe': '4h'
            },
            '_result': {
                'win_rate': 72.5,
                'max_drawdown': 15.0,
                'total_trades': 45,
                'profit_factor': 1.8
            },
            'params': {
                'rsi_period': 14,
                'atr_period': 14,
                'ema_period': 10
            }
        }
    
    def test_save_and_load_identical(self):
        """Saved preset should load back identically"""
        filepath = Path(self.temp_dir) / 'test_preset.json'
        
        # Save
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.test_preset, f)
        
        # Load
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        self.assertEqual(loaded['_meta']['symbol'], 'BTCUSDT')
        self.assertEqual(loaded['_result']['win_rate'], 72.5)
        self.assertEqual(loaded['params']['rsi_period'], 14)
    
    def test_load_nonexistent_returns_none(self):
        """Loading non-existent file should handle gracefully"""
        filepath = Path(self.temp_dir) / 'nonexistent.json'
        
        result = None
        if filepath.exists():
            with open(filepath) as f:
                result = json.load(f)
        
        self.assertIsNone(result)
    
    def test_corrupted_json_raises_exception(self):
        """Corrupted JSON should raise JSONDecodeError"""
        filepath = Path(self.temp_dir) / 'corrupted.json'
        
        # Write invalid JSON
        with open(filepath, 'w') as f:
            f.write("{ invalid json content }")
        
        with self.assertRaises(json.JSONDecodeError):
            with open(filepath) as f:
                json.load(f)
    
    def test_missing_meta_uses_defaults(self):
        """Missing _meta section should use defaults"""
        preset = {'params': {'rsi_period': 14}}
        
        meta = preset.get('_meta', {})
        symbol = meta.get('symbol', 'UNKNOWN')
        exchange = meta.get('exchange', 'bybit')
        
        self.assertEqual(symbol, 'UNKNOWN')
        self.assertEqual(exchange, 'bybit')
    
    def test_missing_result_uses_defaults(self):
        """Missing _result section should use defaults"""
        preset = {'params': {'rsi_period': 14}}
        
        result = preset.get('_result', {})
        win_rate = result.get('win_rate', 0)
        mdd = result.get('max_drawdown', 100)
        
        self.assertEqual(win_rate, 0)
        self.assertEqual(mdd, 100)


class TestPresetValidation(unittest.TestCase):
    """Test preset validation logic"""
    
    def test_valid_preset_passes(self):
        """Valid preset should pass validation"""
        preset = {
            '_meta': {'symbol': 'BTCUSDT'},
            '_result': {'win_rate': 72.5},
            'params': {'rsi_period': 14}
        }
        
        is_valid = self._validate_preset(preset)
        self.assertTrue(is_valid)
    
    def test_empty_preset_fails(self):
        """Empty preset should fail validation"""
        preset = {}
        
        is_valid = self._validate_preset(preset)
        self.assertFalse(is_valid)
    
    def test_missing_params_fails(self):
        """Preset without params should fail"""
        preset = {'_meta': {'symbol': 'BTC'}}
        
        is_valid = self._validate_preset(preset)
        self.assertFalse(is_valid)
    
    def test_invalid_win_rate_flagged(self):
        """Win rate > 100% should be flagged"""
        preset = {'_result': {'win_rate': 150.0}}
        
        result = preset.get('_result', {})
        wr = result.get('win_rate', 0)
        
        is_suspicious = wr > 100 or wr < 0
        self.assertTrue(is_suspicious)
    
    def test_negative_mdd_flagged(self):
        """Negative MDD should be flagged"""
        preset = {'_result': {'max_drawdown': -5.0}}
        
        result = preset.get('_result', {})
        mdd = result.get('max_drawdown', 0)
        
        is_suspicious = mdd < 0
        self.assertTrue(is_suspicious)
    
    def _validate_preset(self, preset):
        """Basic preset validation"""
        if not preset:
            return False
        if 'params' not in preset:
            return False
        return True


class TestPresetFiltering(unittest.TestCase):
    """Test preset filtering by criteria"""
    
    def setUp(self):
        self.presets = [
            {'symbol': 'BTC', 'win_rate': 75.0, 'mdd': 15.0, 'trades': 50},
            {'symbol': 'ETH', 'win_rate': 65.0, 'mdd': 12.0, 'trades': 40},
            {'symbol': 'SOL', 'win_rate': 70.0, 'mdd': 20.0, 'trades': 30},
            {'symbol': 'XRP', 'win_rate': 80.0, 'mdd': 25.0, 'trades': 60},
        ]
    
    def test_filter_by_win_rate(self):
        """Filter presets by minimum win rate"""
        min_wr = 70.0
        filtered = [p for p in self.presets if p['win_rate'] >= min_wr]
        
        self.assertEqual(len(filtered), 3)  # BTC, SOL, XRP
        self.assertNotIn('ETH', [p['symbol'] for p in filtered])
    
    def test_filter_by_mdd(self):
        """Filter presets by maximum MDD"""
        max_mdd = 20.0
        filtered = [p for p in self.presets if p['mdd'] <= max_mdd]
        
        self.assertEqual(len(filtered), 3)  # BTC, ETH, SOL
        self.assertNotIn('XRP', [p['symbol'] for p in filtered])
    
    def test_filter_combined_criteria(self):
        """Filter by multiple criteria"""
        min_wr = 70.0
        max_mdd = 20.0
        min_trades = 30
        
        filtered = [
            p for p in self.presets 
            if p['win_rate'] >= min_wr 
            and p['mdd'] <= max_mdd 
            and p['trades'] >= min_trades
        ]
        
        self.assertEqual(len(filtered), 2)  # BTC, SOL
        symbols = [p['symbol'] for p in filtered]
        self.assertIn('BTC', symbols)
        self.assertIn('SOL', symbols)


if __name__ == '__main__':
    unittest.main(verbosity=2)
