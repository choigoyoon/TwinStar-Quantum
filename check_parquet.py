import pandas as pd
import os

files = [f for f in os.listdir('data/cache') if f.endswith('.parquet')]
sizes = []
for f in files:
    try:
        df = pd.read_parquet(f'data/cache/{f}')
        sizes.append((f, len(df)))
    except:
        pass

sizes.sort(key=lambda x: -x[1])
for name, rows in sizes[:20]:
    print(f"{rows:>10,} rows: {name}")
