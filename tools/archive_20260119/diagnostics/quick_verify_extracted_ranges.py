"""Meta 추출 범위 적절성 검증

이 스크립트는 Meta 최적화로 추출된 범위가 적절한지 검증합니다:
1. Meta 범위 vs 문헌 범위 비교
2. 범위 밖 파라미터 테스트 (atr_mult=3.0, 5.0)
3. 성능 저하 정도 측정

Usage:
    python tools/quick_verify_extracted_ranges.py

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


# 문헌 기반 기본 범위 (config/meta_ranges.py와 동일)
LITERATURE_RANGES = {
    'atr_mult': [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
    'filter_tf': ['2h', '4h', '6h', '12h', '1d'],
    'trail_start_r': [0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0],
    'trail_dist_r': [0.015, 0.02, 0.025, 0.03, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3],
    'entry_validity_hours': [6, 12, 24, 36, 48, 72, 96]
}


def test_params(df, params, label):
    """파라미터 테스트"""
    strategy = AlphaX7Core(use_mtf=True)
    trades = strategy.run_backtest(
        df_pattern=df,
        df_entry=df,
        slippage=0.0005,
        pattern_tolerance=0.05,
        enable_pullback=False,
        **params
    )

    if not trades:
        return None

    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    print(f"\n{label}")
    print("-"*80)
    for k, v in params.items():
        print(f"  {k:22s}: {v}")
    print()
    print(f"  Sharpe Ratio   : {metrics['sharpe_ratio']:10.2f}")
    print(f"  Win Rate       : {metrics['win_rate']:9.1f}%")
    print(f"  MDD            : {metrics['mdd']:9.2f}%")
    print(f"  Profit Factor  : {metrics['profit_factor']:10.2f}")
    print(f"  Total Trades   : {metrics['total_trades']:10d}")

    return metrics


def main():
    # Meta 결과 로드
    meta_file = 'presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json'

    print("="*100)
    print("Meta 추출 범위 적절성 검증")
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

    df = dm.df_entry_full.copy().set_index('timestamp')
    df = df.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df = df.reset_index()
    df = add_all_indicators(df, inplace=False)

    print(f"데이터: {len(df)}개 캔들")

    # 2. Meta 범위 vs 문헌 범위 비교
    print("\n" + "="*100)
    print("2. Meta 범위 vs 문헌 범위 비교")
    print("="*100)

    p = meta['param_ranges_by_mode']

    for param in ['atr_mult', 'filter_tf', 'trail_start_r', 'trail_dist_r', 'entry_validity_hours']:
        meta_range = p[param]['quick']
        lit_range = LITERATURE_RANGES[param]

        print(f"\n{param}:")
        print(f"  Meta 범위  : {meta_range}")
        print(f"  문헌 범위  : {lit_range}")

        # 범위 폭 비교
        if isinstance(meta_range[0], (int, float)):
            meta_width = max(meta_range) - min(meta_range)
            lit_width = max(lit_range) - min(lit_range)
            coverage = meta_width / lit_width * 100 if lit_width > 0 else 0
            print(f"  범위 커버율: {coverage:.1f}% (Meta/문헌)")

    # 3. 범위 밖 파라미터 테스트
    print("\n" + "="*100)
    print("3. 범위 밖 파라미터 테스트")
    print("="*100)

    # 기본 최적 파라미터 (Meta Quick 시작값)
    base_params = {
        'atr_mult': p['atr_mult']['quick'][0],
        'filter_tf': p['filter_tf']['quick'][0],
        'trail_start_r': p['trail_start_r']['quick'][0],
        'trail_dist_r': p['trail_dist_r']['quick'][0],
        'entry_validity_hours': p['entry_validity_hours']['quick'][0]
    }

    print("\n기본 파라미터 (Meta 최적):")
    base_result = test_params(df, base_params, "[1] Meta 최적 (atr_mult=0.5)")

    if not base_result:
        print("기본 백테스트 실패")
        return

    base_sharpe = base_result['sharpe_ratio']

    # 범위 밖 테스트 1: atr_mult=3.0
    params_outside_1 = base_params.copy()
    params_outside_1['atr_mult'] = 3.0

    result_1 = test_params(df, params_outside_1, "[2] 범위 밖 (atr_mult=3.0)")

    # 범위 밖 테스트 2: atr_mult=5.0
    params_outside_2 = base_params.copy()
    params_outside_2['atr_mult'] = 5.0

    result_2 = test_params(df, params_outside_2, "[3] 범위 밖 (atr_mult=5.0)")

    # 4. 성능 저하 분석
    print("\n" + "="*100)
    print("4. 성능 저하 분석")
    print("="*100)

    print(f"\n{'Parameter':<20s} {'Sharpe':>10s} {'Change':>10s} {'판단':<20s}")
    print("-"*70)

    print(f"{'Meta 최적 (0.5)':<20s} {base_sharpe:10.2f} {'baseline':>10s} {'기준':<20s}")

    if result_1:
        sharpe_1 = result_1['sharpe_ratio']
        change_1 = (sharpe_1 - base_sharpe) / base_sharpe * 100 if base_sharpe > 0 else 0
        judgment_1 = "✅ 정상" if change_1 > -20 else "⚠️ 과적합 의심" if change_1 > -50 else "❌ 과적합 확정"
        print(f"{'atr_mult=3.0':<20s} {sharpe_1:10.2f} {change_1:+9.1f}% {judgment_1:<20s}")

    if result_2:
        sharpe_2 = result_2['sharpe_ratio']
        change_2 = (sharpe_2 - base_sharpe) / base_sharpe * 100 if base_sharpe > 0 else 0
        judgment_2 = "✅ 정상" if change_2 > -20 else "⚠️ 과적합 의심" if change_2 > -50 else "❌ 과적합 확정"
        print(f"{'atr_mult=5.0':<20s} {sharpe_2:10.2f} {change_2:+9.1f}% {judgment_2:<20s}")

    # 5. 최종 판단
    print("\n" + "="*100)
    print("5. 최종 판단")
    print("="*100)

    all_changes = []
    if result_1:
        all_changes.append((sharpe_1 - base_sharpe) / base_sharpe * 100 if base_sharpe > 0 else 0)
    if result_2:
        all_changes.append((sharpe_2 - base_sharpe) / base_sharpe * 100 if base_sharpe > 0 else 0)

    if all_changes:
        avg_degradation = sum(all_changes) / len(all_changes)

        print(f"\n평균 성능 저하: {avg_degradation:.1f}%")

        if avg_degradation > -20:
            print("  → ✅ 정상: Meta 범위가 적절함 (범위 밖 성능 저하 <20%)")
        elif avg_degradation > -50:
            print("  → ⚠️ 주의: 과적합 가능성 있음 (범위 밖 성능 저하 20-50%)")
        else:
            print("  → ❌ 경고: 과적합 의심 (범위 밖 성능 저하 >50%)")
            print("  → 권장: Meta 최적화 재실행 (sample_size 증가)")

    print("\n" + "="*100)
    print("검증 완료")
    print("="*100)


if __name__ == '__main__':
    main()
