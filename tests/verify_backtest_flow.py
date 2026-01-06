"""
Verify Backtest Flow (Step 2)
- Tests: Preset Loading, Criteria Validation, Status Update
"""
import sys
import os
import unittest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.batch_verifier import BatchVerifier
from utils.preset_manager import get_preset_manager

class TestBacktestFlow(unittest.TestCase):
    def setUp(self):
        self.verifier = BatchVerifier()
        self.pm = get_preset_manager()
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
    def test_verification_logic(self):
        print("\n\n=== [Step 2] Verifying Backtest Flow ===")
        
        # 1. Criteria
        min_wr = 75.0  
        max_mdd = 15.0 
        print(f"▶️ Settings: Min WR={min_wr}%, Max MDD={max_mdd}%")
        
        # 2. Run Verification
        results = self.verifier.verify_presets(
            self.test_symbols, 
            min_wr=min_wr, 
            max_mdd=max_mdd
        )
        
        print(f"▶️ Analyzed {len(results)} presets")
        
        # 3. Check Logic
        for res in results:
            sym = res['symbol']
            passed = res['passed']
            wr = res.get('win_rate', 0)
            mdd = res.get('mdd', 0)
            
            # Auto-verification logic check
            expected = (wr >= min_wr) and (mdd <= max_mdd)
            self.assertEqual(passed, expected, f"Logic mismatch for {sym}")
            print(f"  - {sym}: WR={wr}%, MDD={mdd}% -> Passed? {passed} [{'OK' if passed==expected else 'FAIL'}]")
            
            # 4. Status Update (Mock save)
            if passed:
                preset_name = Path(res['path']).stem
                success = self.pm.set_verified(preset_name, {'passed': True, 'win_rate': wr})
                self.assertTrue(success, f"Failed to save verified status for {preset_name}")
                print(f"     -> Verified Saved: {preset_name}")
                
if __name__ == '__main__':
    unittest.main()
