"""Meta 최적화 결과로 간단 백테스트

추출된 파라미터로 직접 백테스트 실행

Usage:
    python tools/simple_meta_backtest.py

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import json
import pandas as pd
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics


def main():
    # 1. Meta 결과 로드
    json_path = 'presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json'
    print(f"Meta 결과 로드: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        meta_result = json.load(f)

    print(f"\n[Meta 정보]")
    print(f"  거래소: {meta_result['exchange']}")
    print(f"  심볼: {meta_result['symbol']}")
    print(f"  타임프레임: {meta_result['timeframe']}")
    print(f"  반복: {meta_result['iterations']}회")
    print(f"  최고 점수: {meta_result['statistics']['top_score_history']}")

    # 2. 데이터 로드
    print(f"\n[데이터 로드]")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    dm.load_historical()

    # 리샘플링
    df_15m = dm.df_entry_full.copy()
    df_15m = df_15m.set_index('timestamp')
    df_1h = df_15m.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df_1h = df_1h.reset_index()
    df_1h = add_all_indicators(df_1h, inplace=False)

    print(f"  데이터: {len(df_1h)}개 캔들")
    print(f"  기간: {df_1h['timestamp'].iloc[0]} ~ {df_1h['timestamp'].iloc[-1]}")

    # 3. Quick 모드 파라미터 추출
    print(f"\n[Quick 모드 파라미터]")
    params_by_mode = meta_result['param_ranges_by_mode']

    # Quick: 각 파라미터의 양 끝값 조합 테스트
    quick_params = {}
    for param, modes in params_by_mode.items():
        quick_values = modes['quick']
        quick_params[param] = quick_values
        print(f"  {param:22s}: {quick_values}")

    # 4. 최적 조합 선택 (첫 번째 값들)
    test_params = {
        'atr_mult': quick_params['atr_mult'][0],
        'filter_tf': quick_params['filter_tf'][0],
        'trail_start_r': quick_params['trail_start_r'][0],
        'trail_dist_r': quick_params['trail_dist_r'][0],
        'entry_validity_hours': quick_params['entry_validity_hours'][0]
    }

    print(f"\n[테스트 파라미터]")
    for k, v in test_params.items():
        print(f"  {k:25s}: {v}")

    # 5. 백테스트 실행
    print(f"\n[백테스트 실행]")
    strategy = AlphaX7Core(use_mtf=True)

    trades = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df_1h,
        slippage=0.0005,
        atr_mult=test_params['atr_mult'],
        trail_start_r=test_params['trail_start_r'],
        trail_dist_r=test_params['trail_dist_r'],
        entry_validity_hours=test_params['entry_validity_hours'],
        filter_tf=test_params['filter_tf'],
        pattern_tolerance=0.05,
        pullback_rsi_long=35,
        pullback_rsi_short=65,
        max_adds=1,
        enable_pullback=False
    )

    print(f"  거래 수: {len(trades) if trades else 0}")

    # 6. 메트릭 계산
    if trades and len(trades) > 0:
        print(f"\n[백테스트 결과]")
        metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  MDD: {metrics['mdd']:.2f}%")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Total PnL: {metrics['total_pnl']:.2f}%")
        print(f"  Final Capital: {metrics['final_capital']:.2f}")

        # 7. 다른 조합도 테스트
        print(f"\n[다른 조합 테스트]")

        # 조합 2: 마지막 값들
        test_params_2 = {
            'atr_mult': quick_params['atr_mult'][-1],
            'filter_tf': quick_params['filter_tf'][-1],
            'trail_start_r': quick_params['trail_start_r'][-1],
            'trail_dist_r': quick_params['trail_dist_r'][-1],
            'entry_validity_hours': quick_params['entry_validity_hours'][-1]
        }

        print(f"\n조합 2:")
        for k, v in test_params_2.items():
            print(f"  {k:25s}: {v}")

        trades_2 = strategy.run_backtest(
            df_pattern=df_1h,
            df_entry=df_1h,
            slippage=0.0005,
            atr_mult=test_params_2['atr_mult'],
            trail_start_r=test_params_2['trail_start_r'],
            trail_dist_r=test_params_2['trail_dist_r'],
            entry_validity_hours=test_params_2['entry_validity_hours'],
            filter_tf=test_params_2['filter_tf'],
            pattern_tolerance=0.05,
            pullback_rsi_long=35,
            pullback_rsi_short=65,
            max_adds=1,
            enable_pullback=False
        )

        if trades_2 and len(trades_2) > 0:
            metrics_2 = calculate_backtest_metrics(trades_2, leverage=1, capital=100.0)
            print(f"\n결과:")
            print(f"  Sharpe Ratio: {metrics_2['sharpe_ratio']:.2f}")
            print(f"  Win Rate: {metrics_2['win_rate']:.1f}%")
            print(f"  MDD: {metrics_2['mdd']:.2f}%")
            print(f"  Profit Factor: {metrics_2['profit_factor']:.2f}")
            print(f"  Total Trades: {metrics_2['total_trades']}")
        else:
            print(f"\n결과: 거래 없음")

    else:
        print(f"\n[X] 거래 없음")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    main()
