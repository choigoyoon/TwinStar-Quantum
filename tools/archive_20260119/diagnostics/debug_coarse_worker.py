#!/usr/bin/env python3
"""
Coarse Grid 워커 함수 디버깅 스크립트

단일 파라미터 조합으로 백테스트를 실행하여
워커 함수가 제대로 동작하는지 확인합니다.
"""

import sys
from pathlib import Path

# Root 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from core.optimizer import _worker_run_single
from config.parameters import DEFAULT_PARAMS


def main():
    print("=" * 70)
    print("Coarse Grid 워커 함수 디버깅")
    print("=" * 70)

    # 1. 데이터 로드
    print("\n📂 데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None or df_15m.empty:
        print("❌ 데이터 로드 실패")
        return 1

    print(f"✓ 15분봉 로드: {len(df_15m):,}개")

    # 2. 리샘플링
    print("\n🔄 리샘플링 중... (15m → 1h)")
    from utils.data_utils import resample_data
    df_1h = resample_data(df_15m, '1h', add_indicators=True)

    if df_1h is None or df_1h.empty:
        print("❌ 리샘플링 실패")
        return 1

    print(f"✓ 1시간봉: {len(df_1h):,}개")

    # 3. 테스트 파라미터 (Coarse Grid 기본값)
    print("\n📊 테스트 파라미터:")
    test_params = {
        'trend_interval': '1h',
        'atr_mult': 2.0,
        'filter_tf': '4h',
        'trail_start_r': 2.0,
        'trail_dist_r': 0.020,
        'entry_validity_hours': 48.0,
        'leverage': 3,
        'direction': 'Both',
        'use_mtf': True
    }

    for k, v in test_params.items():
        print(f"  {k}: {v}")

    # 4. 워커 함수 실행
    print("\n🚀 워커 함수 실행 중...")
    try:
        result = _worker_run_single(
            strategy_class=AlphaX7Core,
            params=test_params,
            df_pattern=df_1h,  # trend_interval용
            df_entry=df_1h,    # entry_tf용 (동일)
            slippage=DEFAULT_PARAMS.get('slippage', 0.0004),
            fee=DEFAULT_PARAMS.get('fee', 0.0004)
        )

        if result is None:
            print("❌ 워커 함수가 None 반환")
            print("\n가능한 원인:")
            print("  1. 거래 수가 0개")
            print("  2. 거래 수가 min_trades 미만")
            print("  3. 방향 필터링 후 거래 없음")
            print("  4. MDD 필터 초과")
            print("  5. 백테스트 실행 중 예외 발생")
            return 1

        print("✅ 워커 함수 성공!")
        print(f"\n📈 결과:")
        print(f"  총 거래: {result.trades}회")
        print(f"  승률: {result.win_rate:.1f}%")
        print(f"  MDD: {result.max_drawdown:.2f}%")
        print(f"  Sharpe: {result.sharpe_ratio:.2f}")
        print(f"  Profit Factor: {result.profit_factor:.2f}")
        print(f"  등급: {result.grade}")

        return 0

    except Exception as e:
        print(f"❌ 워커 함수 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
