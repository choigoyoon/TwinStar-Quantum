import sys
import os
import traceback

# Mimic staru_main.py behavior
current_dir = os.path.dirname(os.path.abspath(__file__)) # c:\매매전략\GUI
project_root = os.path.dirname(current_dir) # c:\매매전략

sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)

print(f"Paths added: {project_root}, {current_dir}")

print("\n--- Attempting to import TradingDashboard ---")
try:
    # Try direct import first (as if in GUI package)
    import trading_dashboard
    print("✅ Success: import trading_dashboard")
except Exception:
    print("❌ Failed: import trading_dashboard")
    traceback.print_exc()

    print("\n--- Attempting relative import ---")
    try:
        from GUI import trading_dashboard
        print("✅ Success: from GUI import trading_dashboard")
    except Exception:
        print("❌ Failed: from GUI import trading_dashboard")
        traceback.print_exc()
