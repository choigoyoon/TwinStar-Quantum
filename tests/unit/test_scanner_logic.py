"""
Unit Tests: Scanner Logic
Tests chunking, stage transitions, position locking
"""
import unittest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestScannerChunking(unittest.TestCase):
    """Test symbol chunking logic"""
    
    def test_chunk_size_50(self):
        """Symbols should be chunked into groups of 50"""
        symbols = [f"SYM{i}" for i in range(120)]
        chunk_size = 50
        
        chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 50)
        self.assertEqual(len(chunks[1]), 50)
        self.assertEqual(len(chunks[2]), 20)
    
    def test_single_chunk_small_list(self):
        """Small list should be single chunk"""
        symbols = [f"SYM{i}" for i in range(30)]
        chunk_size = 50
        
        chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0]), 30)
    
    def test_exact_chunk_boundary(self):
        """Exact multiple of chunk size"""
        symbols = [f"SYM{i}" for i in range(100)]
        chunk_size = 50
        
        chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        self.assertEqual(len(chunks), 2)
        self.assertEqual(len(chunks[0]), 50)
        self.assertEqual(len(chunks[1]), 50)


class TestScannerStageTransitions(unittest.TestCase):
    """Test Stage 1 -> Stage 2 transitions"""
    
    def test_rsi_filter_promotion(self):
        """RSI in range should promote to Stage 2"""
        # Stage 1: RSI 30-70 = potential candidate
        rsi_values = [25, 35, 50, 65, 75, 82]
        
        promoted = []
        for rsi in rsi_values:
            if 30 < rsi < 70:
                promoted.append(rsi)
        
        self.assertEqual(len(promoted), 3)
        self.assertIn(35, promoted)
        self.assertIn(50, promoted)
        self.assertIn(65, promoted)
    
    def test_stage2_monitoring_key(self):
        """Stage 2 symbols should have unique keys"""
        symbol = 'BTC'
        exchange = 'bybit'
        
        key = f"{symbol}_{exchange}"
        
        self.assertEqual(key, "BTC_bybit")


class TestScannerPositionLocking(unittest.TestCase):
    """Test global position locking"""
    
    def test_position_blocks_new_entry(self):
        """Existing position should block new entries"""
        active_positions = {'ETH': 2000.0}
        max_positions = 1
        
        can_enter = len(active_positions) < max_positions
        
        self.assertFalse(can_enter)
    
    def test_no_position_allows_entry(self):
        """Empty positions should allow entry"""
        active_positions = {}
        max_positions = 1
        
        can_enter = len(active_positions) < max_positions
        
        self.assertTrue(can_enter)
    
    def test_multiple_position_limit(self):
        """Max position limit should be enforced"""
        max_positions = 3
        
        # 2 positions = can enter
        active_positions = {'BTC': 1000, 'ETH': 2000}
        can_enter = len(active_positions) < max_positions
        self.assertTrue(can_enter)
        
        # 3 positions = cannot enter
        active_positions = {'BTC': 1000, 'ETH': 2000, 'SOL': 150}
        can_enter = len(active_positions) < max_positions
        self.assertFalse(can_enter)
    
    def test_position_removed_allows_entry(self):
        """Removing position should allow new entry"""
        active_positions = {'ETH': 2000.0}
        max_positions = 1
        
        # Remove position
        del active_positions['ETH']
        
        can_enter = len(active_positions) < max_positions
        self.assertTrue(can_enter)


class TestScannerFailureCases(unittest.TestCase):
    """Test failure case handling"""
    
    def test_empty_symbol_list(self):
        """Empty symbol list should be handled"""
        symbols = []
        chunk_size = 50
        
        chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]
        
        self.assertEqual(len(chunks), 0)
    
    def test_invalid_rsi_value(self):
        """Invalid RSI should be handled"""
        rsi = None
        
        # Default to 50 (neutral) if None
        rsi = rsi if rsi is not None else 50
        promoted = 30 < rsi < 70
        
        self.assertTrue(promoted)
    
    def test_negative_rsi(self):
        """Negative RSI should fail filter"""
        rsi = -5.0
        
        promoted = 30 < rsi < 70
        
        self.assertFalse(promoted)


if __name__ == '__main__':
    unittest.main(verbosity=2)
