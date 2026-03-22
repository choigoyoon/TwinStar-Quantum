import sys
import os
import traceback

# Logging
import logging
logger = logging.getLogger(__name__)

# Mimic staru_main.py behavior
current_dir = os.path.dirname(os.path.abspath(__file__)) # c:\매매전략\GUI
project_root = os.path.dirname(current_dir) # c:\매매전략

sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)

logger.info(f"Paths added: {project_root}, {current_dir}")

logger.info("\n--- Attempting to import TradingDashboard ---")
try:
    # Try direct import first (as if in GUI package)
    logger.info("✅ Success: import trading_dashboard")
except Exception:
    logger.info("❌ Failed: import trading_dashboard")
    traceback.print_exc()

    logger.info("\n--- Attempting relative import ---")
    try:
        logger.info("✅ Success: from GUI import trading_dashboard")
    except Exception:
        logger.info("❌ Failed: from GUI import trading_dashboard")
        traceback.print_exc()
