"""
Batch Verifier Logic
- Validates presets against strict criteria (Win Rate, MDD, Grade)
- Returns verification results for UI display
"""
import json
import os
from pathlib import Path

class BatchVerifier:
    def __init__(self, preset_dir="config/presets"):
        self.preset_dir = Path(preset_dir)

    def verify_presets(self, symbols, min_wr=70.0, max_mdd=20.0, min_grade='B'):
        results = []
        
        grade_value = {'S': 4, 'A': 3, 'B': 2, 'C': 1, 'D': 0}
        target_grade_val = grade_value.get(min_grade, 0)
        
        for symbol in symbols:
            preset_path = self.preset_dir / f"bybit_{symbol}_1h.json" # Assuming standard naming
            # Try flexible search if exact mismatch
            if not preset_path.exists():
                # Search for any preset with symbol
                candidates = list(self.preset_dir.glob(f"*{symbol}*.json"))
                if candidates:
                    preset_path = candidates[0] # Pick first found
            
            if preset_path.exists():
                try:
                    with open(preset_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract stats
                    result_block = data.get('_result', {})
                    # Try result block first, then root (legacy)
                    wr = float(result_block.get('win_rate', data.get('win_rate', 0)))
                    mdd = float(result_block.get('max_drawdown', data.get('max_drawdown', 100)))
                    if 'mdd' in result_block:
                        mdd = float(result_block['mdd'])
                        
                    grade = result_block.get('grade', data.get('grade', 'C'))
                    
                    passed = (wr >= min_wr) and (mdd <= max_mdd) and (grade_value.get(grade, 0) >= target_grade_val)
                    
                    results.append({
                        'symbol': symbol,
                        'win_rate': wr,
                        'mdd': mdd,
                        'grade': grade,
                        'passed': passed,
                        'path': str(preset_path)
                    })
                except Exception as e:
                    results.append({'symbol': symbol, 'error': str(e), 'passed': False})
            else:
                results.append({'symbol': symbol, 'error': "Preset Not Found", 'passed': False})
                
        return results

    def save_verification_status(self, results):
        """Mark passed presets as verified in metadata (future implementation)"""
        pass
