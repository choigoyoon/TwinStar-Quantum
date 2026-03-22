# simple_test.py - 간단한 테스트
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Step 1: Import test")

try:
    import pandas as pd
    print("  pandas OK")
except Exception as e:
    print(f"  pandas FAIL: {e}")

try:
    from core.strategy_core import AlphaX7Core
    print("  AlphaX7Core OK")
except Exception as e:
    print(f"  AlphaX7Core FAIL: {e}")

try:
    from tools.realtime_simulator import RealtimeSimulator
    print("  RealtimeSimulator OK")
except Exception as e:
    print(f"  RealtimeSimulator FAIL: {e}")

print("\nStep 2: Data load test")
try:
    df = pd.read_parquet("data/cache/bybit_btcusdt_15m.parquet")
    print(f"  Data loaded: {len(df)} rows")
except Exception as e:
    print(f"  Data load FAIL: {e}")

print("\nStep 3: Simulator test")
try:
    sim = RealtimeSimulator("data/cache/bybit_btcusdt_15m.parquet", "default")
    sim.load_data()
    print("  Simulator OK")
except Exception as e:
    print(f"  Simulator FAIL: {e}")

print("\nDone!")
