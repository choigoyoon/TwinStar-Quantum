"""데이터 품질 및 백테스트 로직 검증

이 스크립트는 다음을 검증합니다:
1. 데이터 기간 및 품질
2. 슬리피지 영향 분석 (0.05% → 0.5%)
3. Walk-Forward 검증 (In-Sample vs Out-of-Sample)

Usage:
    python check_data.py

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
sys.path.insert(0, '.')

import json
import pandas as pd
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics


def test_slippage_impact(df, params, slippage_values):
    """슬리피지 영향 분석"""
    results = []

    strategy = AlphaX7Core(use_mtf=True)

    for slip in slippage_values:
        trades = strategy.run_backtest(
            df_pattern=df,
            df_entry=df,
            slippage=slip,
            pattern_tolerance=0.05,
            enable_pullback=False,
            **params
        )

        if trades:
            metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)
            results.append({
                'slippage': slip * 100,  # Convert to percentage
                'sharpe': metrics['sharpe_ratio'],
                'win_rate': metrics['win_rate'],
                'mdd': metrics['mdd'],
                'pf': metrics['profit_factor'],
                'trades': metrics['total_trades']
            })

    return results


def walk_forward_test(df, params, split_date):
    """Walk-Forward 검증 (In-Sample vs Out-of-Sample)"""
    # In-Sample (학습 기간)
    df_is = df[df['timestamp'] < split_date]

    # Out-of-Sample (검증 기간)
    df_oos = df[df['timestamp'] >= split_date]

    strategy = AlphaX7Core(use_mtf=True)

    # In-Sample 백테스트
    trades_is = strategy.run_backtest(
        df_pattern=df_is,
        df_entry=df_is,
        slippage=0.0005,
        pattern_tolerance=0.05,
        enable_pullback=False,
        **params
    )

    # Out-of-Sample 백테스트
    trades_oos = strategy.run_backtest(
        df_pattern=df_oos,
        df_entry=df_oos,
        slippage=0.0005,
        pattern_tolerance=0.05,
        enable_pullback=False,
        **params
    )

    results = {}

    if trades_is:
        metrics_is = calculate_backtest_metrics(trades_is, leverage=1, capital=100.0)
        results['in_sample'] = {
            'period': f"{df_is['timestamp'].iloc[0]} ~ {df_is['timestamp'].iloc[-1]}",
            'candles': len(df_is),
            'sharpe': metrics_is['sharpe_ratio'],
            'win_rate': metrics_is['win_rate'],
            'mdd': metrics_is['mdd'],
            'pf': metrics_is['profit_factor'],
            'trades': metrics_is['total_trades']
        }

    if trades_oos:
        metrics_oos = calculate_backtest_metrics(trades_oos, leverage=1, capital=100.0)
        results['out_sample'] = {
            'period': f"{df_oos['timestamp'].iloc[0]} ~ {df_oos['timestamp'].iloc[-1]}",
            'candles': len(df_oos),
            'sharpe': metrics_oos['sharpe_ratio'],
            'win_rate': metrics_oos['win_rate'],
            'mdd': metrics_oos['mdd'],
            'pf': metrics_oos['profit_factor'],
            'trades': metrics_oos['total_trades']
        }

        # 성능 저하 계산
        if trades_is:
            is_sharpe = metrics_is['sharpe_ratio']
            oos_sharpe = metrics_oos['sharpe_ratio']
            if is_sharpe > 0:
                degradation = (is_sharpe - oos_sharpe) / is_sharpe * 100
                results['degradation'] = degradation

    return results


def main():
    # Meta 결과 로드
    meta_file = 'presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json'

    print("="*100)
    print("데이터 품질 및 백테스트 로직 검증")
    print("="*100)

    with open(meta_file, 'r') as f:
        meta = json.load(f)

    # 데이터 로드
    print("\n1. 데이터 로드")
    print("-"*100)

    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    dm.load_historical()

    if dm.df_entry_full is None:
        print("데이터 로드 실패")
        return

    df_15m = dm.df_entry_full.copy()
    print(f"15m 데이터: {len(df_15m):,}개 캔들")

    # 1h로 리샘플링
    df = df_15m.set_index('timestamp')
    df = df.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df = df.reset_index()
    df = add_all_indicators(df, inplace=False)

    print(f"1h 데이터: {len(df):,}개 캔들")

    # 데이터 기간 계산
    start_date = df['timestamp'].iloc[0]
    end_date = df['timestamp'].iloc[-1]
    days = (end_date - start_date).days
    years = days / 365.25

    print(f"기간: {start_date} ~ {end_date}")
    print(f"일수: {days}일 ({years:.2f}년)")

    # Quick 파라미터 (최적)
    p = meta['param_ranges_by_mode']
    params = {
        'atr_mult': p['atr_mult']['quick'][0],
        'filter_tf': p['filter_tf']['quick'][0],
        'trail_start_r': p['trail_start_r']['quick'][0],
        'trail_dist_r': p['trail_dist_r']['quick'][0],
        'entry_validity_hours': p['entry_validity_hours']['quick'][0]
    }

    print("\n최적 파라미터:")
    for k, v in params.items():
        print(f"  {k}: {v}")

    # 2. 슬리피지 영향 분석
    print("\n" + "="*100)
    print("2. 슬리피지 영향 분석")
    print("="*100)

    slippage_values = [0.0005, 0.001, 0.002, 0.005]  # 0.05%, 0.1%, 0.2%, 0.5%

    print("\n슬리피지 테스트 중...")
    slip_results = test_slippage_impact(df, params, slippage_values)

    if slip_results:
        print("\n슬리피지 영향:")
        print(f"{'Slippage':>10s} {'Sharpe':>10s} {'Win Rate':>10s} {'MDD':>10s} {'PF':>10s} {'Trades':>10s}")
        print("-"*70)

        base_sharpe = slip_results[0]['sharpe'] if slip_results else 0

        for r in slip_results:
            slip_pct = f"{r['slippage']:.2f}%"
            sharpe_change = ""
            if base_sharpe > 0 and r['sharpe'] != base_sharpe:
                change_pct = (r['sharpe'] - base_sharpe) / base_sharpe * 100
                sharpe_change = f" ({change_pct:+.1f}%)"

            print(f"{slip_pct:>10s} {r['sharpe']:10.2f}{sharpe_change:<10s} {r['win_rate']:9.1f}% "
                  f"{r['mdd']:9.2f}% {r['pf']:10.2f} {r['trades']:10d}")

    # 3. Walk-Forward 검증
    print("\n" + "="*100)
    print("3. Walk-Forward 검증 (In-Sample vs Out-of-Sample)")
    print("="*100)

    # 분할 시점: 2024-01-01 (약 80% In-Sample, 20% Out-of-Sample)
    split_date = pd.Timestamp('2024-01-01', tz='UTC')

    print(f"\n분할 시점: {split_date}")
    print("In-Sample: 학습 기간 (2020-2023)")
    print("Out-of-Sample: 검증 기간 (2024-2026)")
    print()

    wf_results = walk_forward_test(df, params, split_date)

    if 'in_sample' in wf_results:
        is_data = wf_results['in_sample']
        print(f"In-Sample ({is_data['candles']}개 캔들):")
        print(f"  기간: {is_data['period']}")
        print(f"  Sharpe: {is_data['sharpe']:.2f}")
        print(f"  Win Rate: {is_data['win_rate']:.1f}%")
        print(f"  MDD: {is_data['mdd']:.2f}%")
        print(f"  Profit Factor: {is_data['pf']:.2f}")
        print(f"  Total Trades: {is_data['trades']}")
        print()

    if 'out_sample' in wf_results:
        oos_data = wf_results['out_sample']
        print(f"Out-of-Sample ({oos_data['candles']}개 캔들):")
        print(f"  기간: {oos_data['period']}")
        print(f"  Sharpe: {oos_data['sharpe']:.2f}")
        print(f"  Win Rate: {oos_data['win_rate']:.1f}%")
        print(f"  MDD: {oos_data['mdd']:.2f}%")
        print(f"  Profit Factor: {oos_data['pf']:.2f}")
        print(f"  Total Trades: {oos_data['trades']}")
        print()

    if 'degradation' in wf_results:
        deg = wf_results['degradation']
        print(f"성능 저하: {deg:.1f}%")

        # 과적합 판단
        if deg > 50:
            print("  → ⚠️ 과적합 의심 (성능 저하 >50%)")
        elif deg > 20:
            print("  → ⚠️ 과적합 가능성 (성능 저하 >20%)")
        else:
            print("  → ✅ 정상 범위 (성능 저하 <20%)")

    print("\n" + "="*100)
    print("검증 완료")
    print("="*100)


if __name__ == '__main__':
    main()
