#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""기존 데이터 확인 스크립트"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd

# 기존 Bybit 데이터 확인
parquet_file = 'data/cache/bybit_btcusdt_15m.parquet'

if Path(parquet_file).exists():
    df = pd.read_parquet(parquet_file)

    # 타임스탬프가 int면 datetime으로 변환
    if df['timestamp'].dtype in ['int64', 'int32']:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    print("=" * 80)
    print("기존 Bybit BTCUSDT 15분봉 데이터 현황")
    print("=" * 80)
    print(f"개수: {len(df):,}개")
    print(f"기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    days = (df['timestamp'].max() - df['timestamp'].min()).days
    print(f"일수: {days}일 ({days/365:.1f}년)")
    print(f"파일 크기: {Path(parquet_file).stat().st_size / 1024:.1f} KB")
    print()

    if len(df) >= 200000:
        print("✅ 이미 20만 개 이상 수집되어 있습니다!")
        print("   → 추가 수집 불필요")
    else:
        print(f"⚠️  현재 {len(df):,}개, 목표 200,000개까지 {200000 - len(df):,}개 더 필요")
        print("   → 추가 수집 권장")

    print()
    print("다음 단계:")
    print("  1. Out-of-Sample 검증: python tools/test_out_of_sample_validation.py")
    print("  2. filter_tf 재검증: python tools/test_filter_tf_hypothesis.py")
else:
    print(f"❌ 파일 없음: {parquet_file}")
    print("   → 데이터 수집 필요: python tools/collect_bybit_full_history.py")
