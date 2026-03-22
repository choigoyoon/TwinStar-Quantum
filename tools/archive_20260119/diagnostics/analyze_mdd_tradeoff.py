#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MDD vs 승률 트레이드오프 분석

Fine Grid 결과에서 MDD 20% 이하 파라미터 찾기
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from utils.data_utils import resample_data


def analyze_mdd_tradeoff():
    """MDD vs 성능 트레이드오프 분석"""
    print("="*70)
    print("MDD vs 성능 트레이드오프 분석")
    print("="*70)

    # 1. 데이터 로드
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None:
        print("❌ 데이터 로드 실패")
        return

    # timestamp 변환
    if 'timestamp' not in df_15m.columns:
        print("❌ timestamp 컬럼 없음")
        return

    if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    else:
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

    # 리샘플링
    df_1h = resample_data(df_15m, '1h', add_indicators=False)

    # 2. Fine Grid 범위 (최적값 기준)
    fine_grid = {
        'trend_interval': ['1h'],
        'atr_mult': [0.8, 1.0, 1.2, 1.5, 2.0],  # 확장 (MDD 낮추기)
        'filter_tf': ['4h', '6h'],  # 안정적 필터
        'trail_start_r': [0.8, 1.0, 1.2],
        'trail_dist_r': [0.015, 0.018, 0.021, 0.025],  # 확장
        'entry_validity_hours': [38.4, 48.0, 57.6, 72.0],  # 확장
        'adx_period': [10.0, 14.0, 18.0],
        'adx_threshold': [15.0, 20.0, 25.0],  # 높임 (약한 추세 제외)
        'strategy_type': ['adx']
    }

    # 3. 최적화 실행
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df_1h,
        strategy_type='adx'
    )

    print(f"\n🔍 최적화 실행 중... (MDD < 20% 목표)")
    results = optimizer.run_optimization(
        df=df_1h,
        grid=fine_grid,
        metric='sharpe_ratio',
        skip_filter=True  # 전체 결과 확인
    )

    # 4. MDD 필터링
    print(f"\n📊 결과 분석")
    print(f"총 조합: {len(results):,}개")

    # MDD 20% 이하
    low_mdd = [r for r in results if r.max_drawdown <= 20.0]
    print(f"MDD ≤20%: {len(low_mdd):,}개")

    # MDD 15% 이하
    very_low_mdd = [r for r in results if r.max_drawdown <= 15.0]
    print(f"MDD ≤15%: {len(very_low_mdd):,}개")

    # 5. 상위 5개 출력
    print(f"\n{'='*70}")
    print(f"MDD ≤20% 상위 5개 (Sharpe Ratio 순)")
    print(f"{'='*70}")

    for i, r in enumerate(low_mdd[:5], 1):
        print(f"\n[{i}] Sharpe={r.sharpe_ratio:.2f}, 승률={r.win_rate:.1f}%, MDD={r.max_drawdown:.2f}%")
        print(f"    atr_mult={r.params['atr_mult']}, adx_threshold={r.params['adx_threshold']}")
        print(f"    trail_dist_r={r.params['trail_dist_r']}, entry_validity_hours={r.params['entry_validity_hours']}")

    # 6. CSV 저장
    if low_mdd:
        df_results = pd.DataFrame([
            {
                'sharpe_ratio': r.sharpe_ratio,
                'win_rate': r.win_rate,
                'mdd': r.max_drawdown,
                'profit_factor': r.profit_factor,
                'trades': r.trades,
                **r.params
            }
            for r in low_mdd[:50]
        ])

        output_path = Path(__file__).parent.parent / 'results' / 'adx_low_mdd_results.csv'
        output_path.parent.mkdir(exist_ok=True)
        df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 저장 완료: {output_path}")


if __name__ == '__main__':
    analyze_mdd_tradeoff()
