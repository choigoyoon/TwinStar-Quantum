"""
데이터 행 수 확인 스크립트
15m vs 1h 데이터 비교
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from core.data_manager import BotDataManager

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()

if dm.df_entry_full is not None:
    df_15m = dm.df_entry_full

    # 15m → 1h 리샘플링
    df_temp = df_15m.set_index('timestamp')
    df_1h = df_temp.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    print(f'15분봉 데이터: {len(df_15m):,}개')
    print(f'1시간봉 데이터: {len(df_1h):,}개')
    print(f'리샘플링 비율: {len(df_15m) / len(df_1h):.2f}:1')
    print(f'')
    print(f'15분봉 기간:')
    print(f'  시작: {df_15m["timestamp"].iloc[0]}')
    print(f'  종료: {df_15m["timestamp"].iloc[-1]}')
    print(f'')
    print(f'1시간봉 기간:')
    print(f'  시작: {df_1h.index[0]}')
    print(f'  종료: {df_1h.index[-1]}')
    print(f'')
    print(f'데이터 완전성:')
    total_days = (df_1h.index[-1] - df_1h.index[0]).days
    expected_1h = total_days * 24
    actual_1h = len(df_1h)
    coverage = actual_1h / expected_1h * 100 if expected_1h > 0 else 0
    print(f'  총 일수: {total_days:,}일')
    print(f'  예상 1h 캔들: {expected_1h:,}개')
    print(f'  실제 1h 캔들: {actual_1h:,}개')
    print(f'  커버리지: {coverage:.1f}%')
else:
    print('데이터 로드 실패')
