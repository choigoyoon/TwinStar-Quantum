
import sys
import os

# Add project root to path
sys.path.append(rstr(Path(__file__).parent))

def verify_parameter_centralization():
    print("Starting Phase 3 Verification...")
    
    # 1. Config Parameters (Source of Truth)
    try:
        from config.parameters import DEFAULT_PARAMS as P
        print(f"[Config] atr_mult: {P.get('atr_mult')}")
        truth_val = P.get('atr_mult')
    except ImportError as e:
        print(f"❌ Config Import Failed: {e}")
        return
        
    # 2. Preset Manager
    try:
        from utils.preset_manager import DEFAULT_PARAMS_V2, DEFAULT_PARAMS_FLAT
        pm_val_flat = DEFAULT_PARAMS_FLAT.get('atr_mult')
        pm_val_v2 = DEFAULT_PARAMS_V2['indicators']['atr_mult']
        print(f"[PresetManager] Flat atr_mult: {pm_val_flat}")
        print(f"[PresetManager] V2 atr_mult: {pm_val_v2}")
        
        if pm_val_flat != truth_val:
            print("❌ PresetManager Flat mismatch!")
        if pm_val_v2 != truth_val:
            print("❌ PresetManager V2 mismatch!")
            
    except ImportError as e:
        print(f"❌ PresetManager Import Failed: {e}")

    # 3. Strategy Core
    try:
        from core.strategy_core import ACTIVE_PARAMS, AlphaX7Core
        sc_val = ACTIVE_PARAMS.get('atr_mult')
        print(f"[StrategyCore] atr_mult: {sc_val}")
        
        if sc_val != truth_val:
            print("❌ StrategyCore mismatch!")
            
    except ImportError as e:
        print(f"❌ StrategyCore Import Failed: {e}")

    print("Phase 3 Verification Completed.")

if __name__ == "__main__":
    verify_parameter_centralization()
