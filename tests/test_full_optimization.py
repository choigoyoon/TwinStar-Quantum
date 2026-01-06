# test_full_optimization.py - 전수 최적화 테스트

import sys
import os
import itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.strategy_core import AlphaX7Core
import pandas as pd

GRID = {
    'macd_fast': [8, 12],
    'macd_slow': [26, 32],
    'atr_mult': [1.8, 2.0],
    'rsi_period': [14, 21]
}

all_combinations = list(itertools.product(*[GRID[k] for k in GRID.keys()]))
print(f"전체 조합: {len(all_combinations)}개")

print("최적화 엔진 컴파일 확인 완료")
