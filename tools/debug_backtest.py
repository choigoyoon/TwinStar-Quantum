#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""백테스트 디버깅 스크립트 - 왜 거래가 생성되지 않는가?"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from config.parameters import DEFAULT_PARAMS
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT')
if not dm.load_historical():
    print("데이터 로드 실패")
    sys.exit(1)

if dm.df_entry_full is None or dm.df_entry_full.empty:
    print("❌ 데이터가 비어있습니다")
    sys.exit(1)

df = dm.df_entry_full
print(f"데이터 로드 완료: {len(df):,}개 캔들")
print(f"기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
print()

# 타임프레임 리샘플링
from core.optimizer import BacktestOptimizer

optimizer = BacktestOptimizer(AlphaX7Core, df)

# df_pattern (trend_interval=1h)
df_pattern = optimizer._resample(df, '1h')
print(f"df_pattern (1h): {len(df_pattern):,}개")

# df_entry (15m 그대로)
df_entry = df.copy()
print(f"df_entry (15m): {len(df_entry):,}개")
print()

# 전략 실행
print("전략 실행 중...")
strategy = AlphaX7Core()

trades = strategy.run_backtest(
    df_pattern=df_pattern,
    df_entry=df_entry,
    slippage=0.001,  # 0.1%
    atr_mult=DEFAULT_PARAMS['atr_mult'],
    trail_start_r=DEFAULT_PARAMS['trail_start_r'],
    trail_dist_r=DEFAULT_PARAMS['trail_dist_r'],
    pattern_tolerance=DEFAULT_PARAMS['pattern_tolerance'],
    entry_validity_hours=DEFAULT_PARAMS['entry_validity_hours'],
    pullback_rsi_long=DEFAULT_PARAMS['pullback_rsi_long'],
    pullback_rsi_short=DEFAULT_PARAMS['pullback_rsi_short'],
    max_adds=DEFAULT_PARAMS['max_adds'],
    filter_tf='4h',
    rsi_period=DEFAULT_PARAMS['rsi_period'],
    atr_period=DEFAULT_PARAMS['atr_period'],
    macd_fast=DEFAULT_PARAMS['macd_fast'],
    macd_slow=DEFAULT_PARAMS['macd_slow'],
    macd_signal=DEFAULT_PARAMS['macd_signal'],
    ema_period=DEFAULT_PARAMS['ema_period'],
    enable_pullback=False
)

print(f"거래 수: {len(trades) if trades else 0}개")

if trades and len(trades) > 0:
    print("\n첫 3개 거래:")
    for i, t in enumerate(trades[:3], 1):
        print(f"  {i}. {t['type']}: PnL={t['pnl']:.2f}%, Entry={t['entry_time']}")
else:
    print("\n❌ 거래가 생성되지 않았습니다!")
    print("\n가능한 원인:")
    print("  1. df_pattern에 지표가 없음 (RSI, ATR, MACD 등)")
    print("  2. df_entry에 지표가 없음")
    print("  3. 신호 조건이 너무 까다로움")
    print("  4. 데이터 타임스탬프 형식 문제")
    print()
    print("df_pattern 컬럼:")
    print(df_pattern.columns.tolist())
    print()
    print("df_entry 컬럼:")
    print(df_entry.columns.tolist())
