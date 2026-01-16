import sys
import os

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_imports():
    print("=== GUI Integration Import Test ===")
    
    modules_to_test = [
        "GUI.exchange_selector_widget",
        "GUI.history_widget",
        "GUI.trading_dashboard"
    ]
    
    success_count = 0
    for mod_name in modules_to_test:
        try:
            print(f"Testing {mod_name}...", end=" ")
            __import__(mod_name)
            print("✅ SUCCESS")
            success_count += 1
        except Exception as e:
            print(f"❌ FAILED")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            
    print(f"\nResult: {success_count}/{len(modules_to_test)} modules imported successfully.")
    return success_count == len(modules_to_test)

if __name__ == "__main__":
    if test_imports():
        sys.exit(0)
    else:
        sys.exit(1)
