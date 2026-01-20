#!/usr/bin/env python3
"""ADX Fine-Tuning 테스트 (v7.25)

MACD 최적 파라미터 기반으로 ADX 파라미터만 세부 최적화

비용 설정:
- 슬리피지: 0% (지정가 주문)
- 수수료: 0.02% (메이커)

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from itertools import product

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.parameters import DEFAULT_PARAMS
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.metrics import calculate_backtest_metrics

# ============ 비용 설정 ============
SLIPPAGE = 0.0       # 0% 슬리피지 (지정가)
FEE = 0.0002         # 0.02% 메이커 수수료
TOTAL_COST = SLIPPAGE + FEE

# ============ v7.25 최적 파라미터 (고정) ============
OPTIMAL_BASE = {
    'atr_mult': 1.25,
    'filter_tf': '4h',
    'trail_start_r': 0.4,
    'trail_dist_r': 0.05,
}

# ============ ADX Fine-Tuning 범위 ============
ADX_FINE_RANGES = {
    'use_adx_filter': [False, True],                    # 2개
    'adx_threshold': [15, 20, 25, 30, 35, 40],         # 6개 (Wilder: 25)
    'adx_period': [10, 12, 14, 16, 18],                # 5개 (Wilder: 14)
}
# 총 조합: 2 * 6 * 5 = 60개
# (use_adx_filter=False일 때는 1개만 카운트 → 실제 유효: 31개)

# Baseline (ADX 없음)
BASELINE_NO_ADX = {
    'sharpe': 27.32,
    'win_rate': 95.7,
    'mdd': 0.8,
    'total_pnl': 826.8,
    'trades': 2192,
    'profit_factor': 26.68,
}


def load_data(exchange: str = 'bybit', symbol: str = 'BTCUSDT', rows: int = 50000) -> Optional[pd.DataFrame]:
    """데이터 로드 (BotDataManager 사용)"""
    print(f"\n📥 데이터 로딩: {exchange} {symbol}")

    dm = BotDataManager(exchange, symbol, {'entry_tf': '1h'})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 로드 실패")
            return None

        df = dm.df_entry_full.copy()

        if len(df) > rows:
            df = df.tail(rows).copy()

        print(f"✅ 데이터: {len(df):,}개 1시간봉")
        if 'timestamp' in df.columns:
            print(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

        return df

    except Exception as e:
        print(f"❌ 데이터 로드 에러: {e}")
        return None


def run_backtest(df: pd.DataFrame, params: dict) -> dict:
    """단일 백테스트 실행"""
    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

    try:
        trades = strategy.run_backtest(
            df_pattern=df,
            df_entry=df,
            slippage=TOTAL_COST,
            **{k: v for k, v in params.items() if k not in ['slippage', 'fee']}
        )

        if isinstance(trades, tuple):
            trades = trades[0]

        if not trades or len(trades) < 10:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'sharpe_ratio': 0,
                'mdd': 100,
                'total_pnl': 0,
                'profit_factor': 0
            }

        return calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    except Exception as e:
        print(f"⚠️ 백테스트 에러: {e}")
        return {
            'total_trades': 0,
            'win_rate': 0,
            'sharpe_ratio': 0,
            'mdd': 100,
            'total_pnl': 0,
            'profit_factor': 0
        }


def get_grade(sharpe: float, win_rate: float, mdd: float, pf: float) -> str:
    """등급 판정 (v7.25)"""
    if sharpe >= 20 and win_rate >= 85 and mdd <= 10 and pf >= 5:
        return 'S'
    if sharpe >= 15 and win_rate >= 80 and mdd <= 15 and pf >= 3:
        return 'A'
    if sharpe >= 10 and win_rate >= 75 and mdd <= 20 and pf >= 2:
        return 'B'
    if sharpe >= 5 and win_rate >= 70 and mdd <= 25 and pf >= 1.5:
        return 'C'
    return 'F'


def main():
    """메인 함수"""
    # Windows 콘솔 UTF-8 인코딩 설정
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("🎯 ADX Fine-Tuning Test (v7.25)")
    print("   Baseline: MACD 최적 파라미터 (Sharpe 27.32, 승률 95.7%, MDD 0.8%)")
    print("   비용: 슬리피지 0% + 수수료 0.02%")
    print("=" * 80)

    # 데이터 로드
    df = load_data(exchange='bybit', symbol='BTCUSDT', rows=50000)
    if df is None:
        print("\n❌ 데이터 로드 실패. 종료합니다.")
        return

    # 조합 생성
    results: List[Dict] = []
    start = datetime.now()

    # Baseline 파라미터
    baseline_params = DEFAULT_PARAMS.copy()
    baseline_params.update(OPTIMAL_BASE)
    baseline_params['leverage'] = 1
    baseline_params['macd_fast'] = 6
    baseline_params['macd_slow'] = 18
    baseline_params['macd_signal'] = 7
    baseline_params['entry_validity_hours'] = 6.0

    print(f"\n📋 탐색 범위:")
    print(f"   use_adx_filter: {ADX_FINE_RANGES['use_adx_filter']}")
    print(f"   adx_threshold: {ADX_FINE_RANGES['adx_threshold']}")
    print(f"   adx_period: {ADX_FINE_RANGES['adx_period']}")

    # 조합 생성 (효율적)
    combos = []

    # ADX 없음 (1개)
    combos.append((False, None, None))

    # ADX 있음 (threshold × period 조합)
    for threshold in ADX_FINE_RANGES['adx_threshold']:
        for period in ADX_FINE_RANGES['adx_period']:
            combos.append((True, threshold, period))

    total = len(combos)
    print(f"\n총 조합: {total}개 (ADX 없음 1개 + ADX 있음 {total-1}개)")

    # 백테스트 실행
    for i, (use_adx, threshold, period) in enumerate(combos, 1):
        test_params = baseline_params.copy()
        test_params['use_adx_filter'] = use_adx

        if use_adx:
            test_params['adx_threshold'] = threshold
            test_params['adx_period'] = period

        m = run_backtest(df, test_params)

        sharpe = m.get('sharpe_ratio', 0)
        win_rate = m.get('win_rate', 0)
        mdd = abs(m.get('mdd', 100))
        pnl = m.get('total_pnl', 0)
        trades = m.get('total_trades', 0) or m.get('trade_count', 0)
        pf = m.get('profit_factor', 0)
        grade = get_grade(sharpe, win_rate, mdd, pf)

        results.append({
            'use_adx': use_adx,
            'adx_threshold': threshold,
            'adx_period': period,
            'sharpe': sharpe,
            'win_rate': win_rate,
            'mdd': mdd,
            'pnl': pnl,
            'trades': trades,
            'pf': pf,
            'grade': grade,
        })

        if i % 10 == 0:
            print(f"   진행: {i}/{total} ({i/total*100:.0f}%)")

    elapsed = (datetime.now() - start).total_seconds()

    # 정렬 (Sharpe 기준)
    results.sort(key=lambda x: x['sharpe'], reverse=True)

    # 상위 15개 출력
    print("\n" + "=" * 105)
    print("🏆 상위 15개 결과 (Sharpe 순)")
    print("=" * 105)
    print(f"{'순위':>4} {'등급':>4} {'ADX':>5} {'임계값':>6} {'주기':>4} {'Sharpe':>8} {'승률':>8} {'MDD':>8} {'PnL':>10} {'거래':>6} {'PF':>6}")
    print("-" * 105)

    for i, r in enumerate(results[:15], 1):
        emoji = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉', 'F': '❌'}.get(r['grade'], '?')
        adx_str = '없음' if not r['use_adx'] else '있음'
        threshold_str = '-' if not r['use_adx'] else str(r['adx_threshold'])
        period_str = '-' if not r['use_adx'] else str(r['adx_period'])

        print(f"{i:>4} {emoji}{r['grade']:>3} {adx_str:>5} {threshold_str:>6} {period_str:>4} "
              f"{r['sharpe']:>8.2f} {r['win_rate']:>7.1f}% {r['mdd']:>7.1f}% "
              f"{r['pnl']:>9.1f}% {r['trades']:>6} {r['pf']:>6.2f}")

    # 최적 조합
    best = results[0]
    baseline = [r for r in results if not r['use_adx']][0]

    print("\n" + "=" * 80)
    print("🎯 최적 조합")
    print("=" * 80)

    if best['use_adx']:
        print("✅ ADX 필터 포함 (성능 향상)")
        print(f"\n```python")
        print("OPTIMAL_PARAMS_WITH_ADX = {")
        print(f"    'atr_mult': {OPTIMAL_BASE['atr_mult']},")
        print(f"    'filter_tf': '{OPTIMAL_BASE['filter_tf']}',")
        print(f"    'trail_start_r': {OPTIMAL_BASE['trail_start_r']},")
        print(f"    'trail_dist_r': {OPTIMAL_BASE['trail_dist_r']},")
        print(f"    'use_adx_filter': True,")
        print(f"    'adx_threshold': {best['adx_threshold']},")
        print(f"    'adx_period': {best['adx_period']},")
        print("}")
        print("```")
    else:
        print("❌ ADX 필터 제외 (성능 저하 또는 동일)")
        print(f"\n```python")
        print("OPTIMAL_PARAMS_NO_ADX = {")
        print(f"    'atr_mult': {OPTIMAL_BASE['atr_mult']},")
        print(f"    'filter_tf': '{OPTIMAL_BASE['filter_tf']}',")
        print(f"    'trail_start_r': {OPTIMAL_BASE['trail_start_r']},")
        print(f"    'trail_dist_r': {OPTIMAL_BASE['trail_dist_r']},")
        print(f"    'use_adx_filter': False,")
        print("}")
        print("```")

    print(f"\n등급: {best['grade']} | Sharpe: {best['sharpe']:.2f} | 승률: {best['win_rate']:.1f}%")
    print(f"MDD: {best['mdd']:.1f}% | PnL: {best['pnl']:.1f}% | 거래: {best['trades']}회 | PF: {best['pf']:.2f}")

    # Baseline 비교
    print("\n" + "-" * 80)
    print("📊 Baseline (ADX 없음) 대비")
    print("-" * 80)
    print(f"{'지표':<12} {'Baseline':>10} {'최적':>10} {'변화':>12} {'판정':>4}")
    print("-" * 52)

    for name, bv, ov in [
        ('Sharpe', baseline['sharpe'], best['sharpe']),
        ('승률', baseline['win_rate'], best['win_rate']),
        ('MDD', baseline['mdd'], best['mdd']),
        ('PnL', baseline['pnl'], best['pnl']),
        ('거래수', baseline['trades'], best['trades']),
        ('PF', baseline['pf'], best['pf']),
    ]:
        diff = ov - bv
        pct_diff = (diff / bv * 100) if bv != 0 else 0

        if name == 'MDD':
            ind = '✅' if diff <= 0 else '⚠️'
        elif name == '거래수':
            ind = '➖' if abs(pct_diff) < 5 else ('⚠️' if pct_diff < -20 else '✅')
        else:
            ind = '✅' if diff >= 0 else '⚠️'

        if name in ['승률', 'MDD', 'PnL']:
            print(f"{name:<12} {bv:>9.1f}% {ov:>9.1f}% {diff:>+9.1f}% {ind:>4}")
        elif name == '거래수':
            print(f"{name:<12} {bv:>10.0f} {ov:>10.0f} {diff:>+10.0f} {ind:>4}")
        else:
            print(f"{name:<12} {bv:>10.2f} {ov:>10.2f} {diff:>+10.2f} {ind:>4}")

    # 시나리오 판단
    sharpe_diff_pct = (best['sharpe'] - baseline['sharpe']) / baseline['sharpe'] * 100

    print("\n" + "=" * 80)
    print("💡 결론")
    print("=" * 80)

    if sharpe_diff_pct >= 5:
        print(f"✅ ADX 필터가 성능을 크게 향상시킴 (+{sharpe_diff_pct:.1f}%)")
        print(f"   → ADX 포함 권장")
    elif sharpe_diff_pct >= 1:
        print(f"⚠️ ADX 필터가 성능을 약간 향상 (+{sharpe_diff_pct:.1f}%)")
        print(f"   → 선택 사항 (복잡도 vs 성능 trade-off)")
    elif sharpe_diff_pct >= -1:
        print(f"➖ ADX 필터 영향 미미 ({sharpe_diff_pct:+.1f}%)")
        print(f"   → ADX 제외 권장 (중복 필터)")
    else:
        print(f"❌ ADX 필터가 성능 저하 ({sharpe_diff_pct:.1f}%)")
        print(f"   → ADX 제외 필수")

    # 결과 저장
    import json
    report_dir = project_root / 'reports' / 'adx_fine_tuning'
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = report_dir / f'adx_fine_tuning_{ts}.json'

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'version': 'v7.25_adx_fine_tuning',
            'cost': {'slippage': SLIPPAGE, 'fee': FEE, 'total': TOTAL_COST},
            'baseline': {
                'params': {**OPTIMAL_BASE, 'use_adx_filter': False},
                'sharpe': float(baseline['sharpe']),
                'win_rate': float(baseline['win_rate']),
                'mdd': float(baseline['mdd']),
                'pnl': float(baseline['pnl']),
                'trades': int(baseline['trades']),
                'pf': float(baseline['pf']),
                'grade': baseline['grade'],
            },
            'best': {
                'params': {
                    **OPTIMAL_BASE,
                    'use_adx_filter': best['use_adx'],
                    'adx_threshold': best['adx_threshold'],
                    'adx_period': best['adx_period'],
                } if best['use_adx'] else {**OPTIMAL_BASE, 'use_adx_filter': False},
                'sharpe': float(best['sharpe']),
                'win_rate': float(best['win_rate']),
                'mdd': float(best['mdd']),
                'pnl': float(best['pnl']),
                'trades': int(best['trades']),
                'pf': float(best['pf']),
                'grade': best['grade'],
            },
            'top_15': [
                {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v)
                 for k, v in r.items()}
                for r in results[:15]
            ],
            'sharpe_diff_pct': float(sharpe_diff_pct),
            'elapsed_seconds': elapsed,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 저장: {json_path}")
    print(f"⏱️ 소요: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print("\n✅ 완료!")


if __name__ == '__main__':
    main()
