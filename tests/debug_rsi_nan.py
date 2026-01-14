import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.indicators import calculate_rsi

def debug_rsi():
    # Setup Data
    np.random.seed(42)  # Fixed seed for reproducibility
    values = np.random.randn(100) + 100 # Price around 100
    values[50:60] = np.nan
    data = pd.Series(values)
    
    print("--- Input Data (48-62) ---")
    print(data.iloc[48:62])
    
    # Calculate RSI
    rsi = calculate_rsi(data, period=14, return_series=True)
    
    print("\n--- RSI Output (48-62) ---")
    print(rsi.iloc[48:62])
    
    # Manually reproduce logic to find divergence
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    print("\n--- Avg Gain (55) ---")
    print(avg_gain.iloc[55])
    print("\n--- Avg Loss (55) ---")
    print(avg_loss.iloc[55])
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    print("\n--- RS (55) ---")
    print(rs.iloc[55])
    
    calc_rsi = 100 - (100 / (1 + rs.fillna(100)))
    print("\n--- Calculated (before fillna(50)) ---")
    print(calc_rsi.iloc[55])

if __name__ == "__main__":
    debug_rsi()
