import pandas as pd
from core.optimization_logic import OptimizationEngine
from core.strategy_core import AlphaX7Core
import os

def test_optimization_logic():
    print("Testing OptimizationEngine...")
    strategy = AlphaX7Core(use_mtf=True)
    engine = OptimizationEngine(strategy=strategy)
    
    data_path = r"data\cache\upbit_btc_15m.parquet"
    if not os.path.exists(data_path):
        print(f"Data not found at {data_path}")
        return
        
    df = pd.read_parquet(data_path).iloc[:500]
    
    params = {
        'atr_mult': 1.5,
        'trail_start_r': 0.8,
        'trail_dist_r': 0.5,
        'leverage': 3
    }
    
    print("Running single backtest via engine...")
    result = engine.run_single_backtest(params, df)
    
    if result:
        print(f"✅ Success: OptimizationResult returned")
        print(f"Results: Simple={result.simple_return:.2f}%, Compound={result.compound_return:.2f}%, MDD={result.max_drawdown:.2f}%, Type={result.strategy_type}")
    else:
        print("❌ Failure: Result is None")

if __name__ == "__main__":
    test_optimization_logic()
