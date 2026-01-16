import pandas as pd
from pathlib import Path

# Check main data file
data_file = Path('data/cache/bybit_btcusdt_15m.parquet')
if data_file.exists():
    df = pd.read_parquet(data_file)
    print(f"=== {data_file.name} ===")
    print(f"Total rows: {len(df):,}")
    print(f"Start: {df.iloc[0]['timestamp']}")
    print(f"End: {df.iloc[-1]['timestamp']}")

    # Calculate date range
    start = pd.to_datetime(df.iloc[0]['timestamp'])
    end = pd.to_datetime(df.iloc[-1]['timestamp'])
    days = (end - start).days
    years = days / 365.25
    print(f"Period: {days} days ({years:.2f} years)")
else:
    print(f"File not found: {data_file}")
