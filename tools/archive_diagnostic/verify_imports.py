
import sys
import os

# Add GUI to path
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"Checking imports for GUI.trading_dashboard...")
try:
    from GUI.trading_dashboard import TradingDashboard
    print("✅ Success: GUI.trading_dashboard imported.")
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
