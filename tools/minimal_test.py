# minimal_test.py - 최소 테스트
import json
result = {"test": "start"}

try:
    import sys
    import os
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, PROJECT_ROOT)
    os.chdir(PROJECT_ROOT)
    result["cwd"] = os.getcwd()
    
    import pandas as pd
    result["pandas"] = "ok"
    
    # parquet 테스트
    df = pd.read_parquet("data/cache/bybit_btcusdt_15m.parquet")
    result["data_rows"] = len(df)
    
    result["status"] = "success"
except Exception as e:
    result["status"] = "error"
    result["error"] = str(e)
    import traceback
    result["trace"] = traceback.format_exc()

# 결과 저장
with open("minimal_result.json", "w") as f:
    json.dump(result, f, indent=2)
