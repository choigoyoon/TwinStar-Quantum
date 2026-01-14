import unittest
import sys
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Imports (Delayed to ensure path setup)
from utils.validators import validate_symbol, validate_exchange, validate_number
from utils.symbol_converter import convert_symbol, extract_base, convert_all_symbols
from utils.logger import get_logger, get_module_logger
from paths import Paths

class TestPhase5Utils(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        try:
            shutil.rmtree(self.temp_dir)
        except OSError:
            pass

    # =========================================================================
    # 1. Validators
    # =========================================================================
    def test_01_validators(self):
        """[Validators] Symbol, Exchange, Number"""
        # Symbol
        self.assertTrue(validate_symbol("BTCUSDT")[0])
        self.assertTrue(validate_symbol("KRW-BTC")[0])
        self.assertFalse(validate_symbol("")[0])
        self.assertFalse(validate_symbol("A")[0]) # Too short
        self.assertFalse(validate_symbol("BTC/USDT")[0]) # Invalid char
        
        # Exchange
        self.assertTrue(validate_exchange("bybit")[0])
        self.assertTrue(validate_exchange("UPBIT")[0])
        self.assertFalse(validate_exchange("invalid_ex")[0])
        
        # Number
        self.assertTrue(validate_number("100", min_val=0)[0])
        self.assertFalse(validate_number("-1", min_val=0)[0])
        self.assertFalse(validate_number("abc")[0])

    # =========================================================================
    # 2. Symbol Converter
    # =========================================================================
    def test_02_symbol_converter(self):
        """[SymbolConverter] Conversion Logic"""
        # Extract Base
        self.assertEqual(extract_base("BTCUSDT"), "BTC")
        self.assertEqual(extract_base("KRW-BTC"), "BTC")
        self.assertEqual(extract_base("BTC_KRW"), "BTC")
        self.assertEqual(extract_base("BTC"), "BTC")
        
        # Convert
        self.assertEqual(convert_symbol("BTC", "bybit"), "BTCUSDT")
        self.assertEqual(convert_symbol("BTC", "upbit"), "KRW-BTC")
        self.assertEqual(convert_symbol("BTC", "bithumb"), "BTC_KRW")
        
        # Batch Convert
        src = ["BTCUSDT", "ETHUSDT"]
        res = convert_all_symbols(src, "bybit", "upbit")
        self.assertEqual(res, ["KRW-BTC", "KRW-ETH"])

    # =========================================================================
    # 3. Data Downloader
    # =========================================================================
    def test_03_data_downloader(self):
        """[DataDownloader] Logic & Hybrid Mode"""
        from utils.data_downloader import download_symbol, get_filtered_symbols
        
        # Mock DataManager
        with patch('utils.data_downloader.DataManager') as MockDM, \
             patch('utils.data_downloader.shutil') as mock_shutil, \
             patch('utils.data_downloader.SymbolCache') as MockSC:
            
            # Setup Mock
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.__len__.return_value = 3
            dm_instance = MockDM.return_value
            dm_instance.download.return_value = mock_df # Return Mock DF behavior
            dm_instance._get_cache_path.return_value = Path("fake_path")
            
            # Normal Download
            count = download_symbol("bybit", "BTCUSDT", "1h")
            self.assertEqual(count, 3)
            dm_instance.download.assert_called_with(symbol="BTCUSDT", exchange="bybit", timeframe="1h", limit=500000)
            
            # Hybrid Download (Bithumb uses Upbit)
            count = download_symbol("bithumb", "BTC_KRW", "1h")
            self.assertEqual(count, 3)
            # Should call download with UPBIT
            dm_instance.download.assert_called_with(symbol="BTC_KRW", exchange="upbit", timeframe="1h", limit=500000)
            # Should try to copy
            mock_shutil.copy.assert_called()

            # Filtered Symbols Mock
            sc_instance = MockSC.return_value
            sc_instance._cache = {
                'exchanges': {
                    'upbit': {'symbols': [{'base': 'BTC', 'quote': 'KRW'}, {'base': 'ETH', 'quote': 'KRW'}]},
                    'bithumb': {'symbols': [{'base': 'BTC', 'quote': 'KRW'}, {'base': 'XRP', 'quote': 'KRW'}]}
                }
            }
            
            # Hybrid Filtering (Intersection)
            hybrid_symbols = get_filtered_symbols("bithumb")
            self.assertIn("BTC", hybrid_symbols)
            self.assertNotIn("ETH", hybrid_symbols) # ETH Only in Upbit
            self.assertNotIn("XRP", hybrid_symbols) # XRP Only in Bithumb (assuming strict intersection logic if that's what code does)
            
            # Wait, verify code logic:
            # upbit_bases = {'BTC', 'ETH'}
            # bithumb_bases = {'BTC', 'XRP'}
            # intersection = {'BTC'}
            # So XRP should NOT be in result.

    # =========================================================================
    # 4. Logger
    # =========================================================================
    def test_04_logger(self):
        """[Logger] Creation & Config"""
        logger = get_module_logger("test_module")
        self.assertTrue(logger.name.endswith("test_module"))
        self.assertTrue(logger.hasHandlers())
        
        # Log Helper
        from utils.logger import LogHelper
        helper = LogHelper(logger)
        with self.assertLogs(logger, level='INFO') as cm:
            helper.success("Test Success")
        self.assertIn("✅ Test Success", cm.output[0])

    # =========================================================================
    # 5. Paths
    # =========================================================================
    def test_05_paths(self):
        """[Paths] Directory Structure"""
        # Check basic constants
        self.assertTrue(str(Paths.BASE).endswith("매매전략") or "TwinStar" in str(Paths.BASE))
        self.assertTrue(str(Paths.USER).endswith("user"))
        self.assertTrue(str(Paths.LOGS).endswith("logs"))
        
        # Ensure Dirs (Mock makedirs to avoid side effects on real sys if possible, but temp dir is handled in tearDown? 
        # Actually Paths uses its own static paths based on __file__.
        # So ensuring dirs might create folders in real project if we are not careful.
        # But Paths.BASE is real project root.
        # verify_only checks existence.
        
        # Just check formatting methods for now
        sym_dir = Paths.symbol_dir("bybit", "BTC/USDT")
        self.assertIn("BTC_USDT", sym_dir) # Replace / with _
        self.assertIn("bybit", sym_dir.lower())

if __name__ == '__main__':
    unittest.main()
