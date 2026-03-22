#!/usr/bin/env python3
"""Phase 2: Fine-Tuning 빠른 테스트 (v7.25)

슬리피지 0% 지정가 기준 - 축소된 범위로 빠른 검증

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

# ============ 축소된 탐색 범위 (빠른 검증용) ============
QUICK_RANGES = {
    'atr_mult': [0.9, 1.0, 1.1, 1.25],       # 4개
    'filter_tf': ['4h', '6h', '8h'],          # 3개
    'trail_start_r': [0.4, 0.6, 0.8],         # 3개
    'trail_dist_r': [0.05, 0.08, 0.1],        # 3개
}
# 총 조합: 4 * 3 * 3 * 3 = 108개

# Phase 1 Baseline
PHASE1_BASELINE = {
    'sharpe': 24.20,
    'win_rate': 91.36,
    'mdd': 4.09,
    'total_pnl': 593.4,
    'trades': 845,
    'profit_factor': 9.78,
}


def validate_filter_tf_hierarchy(entry_tf: str, filter_tfs: list) -> None:
    """필터 TF가 진입 TF보다 큰지 검증

    Args:
        entry_tf: 진입 타임프레임 (예: '1h')
        filter_tfs: 필터 타임프레임 리스트 (예: ['4h', '6h', '8h'])

    Raises:
        AssertionError: filter_tf ≤ entry_tf인 경우
    """
    TF_ORDER = ['15m', '30m', '1h', '2h', '3h', '4h', '6h', '8h', '12h', '1d', '1w']

    try:
        entry_idx = TF_ORDER.index(entry_tf)
    except ValueError:
        raise ValueError(f"❌ 알 수 없는 entry_tf: '{entry_tf}'\n   지원: {TF_ORDER}")

    for ftf in filter_tfs:
        try:
            filter_idx = TF_ORDER.index(ftf)
        except ValueError:
            raise ValueError(f"❌ 알 수 없는 filter_tf: '{ftf}'\n   지원: {TF_ORDER}")

        assert filter_idx > entry_idx, (
            f"❌ filter_tf '{ftf}' must be > entry_tf '{entry_tf}'\n"
            f"   TF hierarchy: {entry_tf} (idx {entry_idx}) < {ftf} (idx {filter_idx})"
        )

    print(f"✅ TF hierarchy validated: entry_tf '{entry_tf}' < filter_tf {filter_tfs}")


def load_data(exchange: str = 'bybit', symbol: str = 'BTCUSDT', rows: int = 50000) -> Optional[pd.DataFrame]:
    """데이터 로드 (BotDataManager 사용)

    Args:
        exchange: 거래소 (기본: bybit)
        symbol: 심볼 (기본: BTCUSDT)
        rows: 최대 행 수 (기본: 50000)

    Returns:
        1시간봉 DataFrame 또는 None
    """
    print(f"\n📥 데이터 로딩: {exchange} {symbol}")

    # BotDataManager 사용 (SSOT)
    dm = BotDataManager(exchange, symbol, {'entry_tf': '1h'})

    try:
        success = dm.load_historical()
        if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
            print("❌ 데이터 로드 실패")
            return None

        df = dm.df_entry_full.copy()

        # 행 수 제한
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
    """단일 백테스트 실행

    Args:
        df: 1시간봉 DataFrame
        params: 파라미터 딕셔너리

    Returns:
        메트릭 딕셔너리
    """
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
    """등급 판정 (v7.25)

    Args:
        sharpe: Sharpe Ratio
        win_rate: 승률 (%)
        mdd: MDD (%)
        pf: Profit Factor

    Returns:
        등급 (S/A/B/C/F)
    """
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
    print("=" * 70)
    print("🎯 Phase 2: Fine-Tuning Quick Test (v7.25)")
    print("   비용: 슬리피지 0% + 수수료 0.02%")
    print("=" * 70)

    # 타임프레임 계층 검증
    entry_tf = '1h'  # BotDataManager에서 로드하는 1시간봉
    validate_filter_tf_hierarchy(entry_tf, QUICK_RANGES['filter_tf'])

    # 데이터 로드
    df = load_data(exchange='bybit', symbol='BTCUSDT', rows=50000)
    if df is None:
        print("\n❌ 데이터 로드 실패. 종료합니다.")
        return

    # 조합 생성
    keys = list(QUICK_RANGES.keys())
    values = [QUICK_RANGES[k] for k in keys]
    combos = list(product(*values))

    total = len(combos)
    print(f"\n탐색 조합: {total}개")
    print(f"파라미터: {', '.join(keys)}")

    # Baseline 파라미터
    baseline_params = DEFAULT_PARAMS.copy()
    baseline_params['leverage'] = 1
    baseline_params['macd_fast'] = 6
    baseline_params['macd_slow'] = 18
    baseline_params['macd_signal'] = 7
    baseline_params['entry_validity_hours'] = 6.0

    # 백테스트 실행
    results: List[Dict] = []
    start = datetime.now()

    for i, combo in enumerate(combos, 1):
        test_params = baseline_params.copy()
        for k, v in zip(keys, combo):
            test_params[k] = v

        m = run_backtest(df, test_params)

        sharpe = m.get('sharpe_ratio', 0)
        win_rate = m.get('win_rate', 0)
        mdd = abs(m.get('mdd', 100))
        pnl = m.get('total_pnl', 0)
        trades = m.get('total_trades', 0) or m.get('trade_count', 0)
        pf = m.get('profit_factor', 0)

        results.append({
            'params': dict(zip(keys, combo)),
            'sharpe': sharpe,
            'win_rate': win_rate,
            'mdd': mdd,
            'pnl': pnl,
            'trades': trades,
            'pf': pf,
            'grade': get_grade(sharpe, win_rate, mdd, pf),
        })

        if i % 20 == 0:
            print(f"   진행: {i}/{total} ({i/total*100:.0f}%)")

    elapsed = (datetime.now() - start).total_seconds()

    # 정렬 (Sharpe 기준)
    results.sort(key=lambda x: x['sharpe'], reverse=True)

    # 상위 15개 출력
    print("\n" + "=" * 100)
    print("🏆 상위 15개 결과 (Sharpe 순)")
    print("=" * 100)
    print(f"{'순위':>4} {'등급':>4} {'Sharpe':>8} {'승률':>8} {'MDD':>8} {'PnL':>10} {'거래':>6} {'PF':>6} 파라미터")
    print("-" * 100)

    for i, r in enumerate(results[:15], 1):
        params_str = ', '.join(f"{k}={v}" for k, v in r['params'].items())
        emoji = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉', 'F': '❌'}.get(r['grade'], '?')
        print(f"{i:>4} {emoji}{r['grade']:>3} {r['sharpe']:>8.2f} {r['win_rate']:>7.1f}% {r['mdd']:>7.1f}% "
              f"{r['pnl']:>9.1f}% {r['trades']:>6} {r['pf']:>6.2f} {params_str}")

    # 최적 조합
    best = results[0]
    print("\n" + "=" * 70)
    print("🎯 최적 조합 (v7.25)")
    print("=" * 70)
    print("```python")
    print("OPTIMAL_PARAMS = {")
    for k, v in sorted(best['params'].items()):
        if isinstance(v, str):
            print(f"    '{k}': '{v}',")
        else:
            print(f"    '{k}': {v},")
    print("}")
    print("```")
    print(f"\n등급: {best['grade']} | Sharpe: {best['sharpe']:.2f} | 승률: {best['win_rate']:.1f}%")
    print(f"MDD: {best['mdd']:.1f}% | PnL: {best['pnl']:.1f}% | 거래: {best['trades']}회 | PF: {best['pf']:.2f}")

    # Baseline 비교
    print("\n" + "-" * 70)
    print("📊 Phase 1 Baseline 대비 (v7.25)")
    print("-" * 70)
    base = PHASE1_BASELINE
    print(f"{'지표':<10} {'Baseline':>10} {'최적':>10} {'변화':>10}")
    print("-" * 45)
    for name, bv, ov in [
        ('Sharpe', base['sharpe'], best['sharpe']),
        ('승률', base['win_rate'], best['win_rate']),
        ('MDD', base['mdd'], best['mdd']),
        ('PnL', base['total_pnl'], best['pnl']),
        ('PF', base['profit_factor'], best['pf']),
    ]:
        diff = ov - bv
        ind = '✅' if (name != 'MDD' and diff >= 0) or (name == 'MDD' and diff <= 0) else '⚠️'
        if name in ['승률', 'MDD', 'PnL']:
            print(f"{name:<10} {bv:>9.1f}% {ov:>9.1f}% {diff:>+9.1f}% {ind}")
        else:
            print(f"{name:<10} {bv:>10.2f} {ov:>10.2f} {diff:>+9.2f} {ind}")

    # 결과 저장
    import json
    report_dir = project_root / 'reports' / 'fine_tuning'
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = report_dir / f'fine_tuning_quick_{ts}.json'

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'version': 'v7.25_quick',
            'cost': {'slippage': SLIPPAGE, 'fee': FEE, 'total': TOTAL_COST},
            'best': {
                'params': best['params'],
                'sharpe': float(best['sharpe']),
                'win_rate': float(best['win_rate']),
                'mdd': float(best['mdd']),
                'pnl': float(best['pnl']),
                'trades': int(best['trades']),
                'pf': float(best['pf']),
                'grade': best['grade'],
            },
            'top_15': [
                {'rank': i+1, **{k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v)
                               for k, v in r.items()}}
                for i, r in enumerate(results[:15])
            ],
            'elapsed_seconds': elapsed,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 저장: {json_path}")
    print(f"⏱️ 소요: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    print("\n✅ 완료!")


if __name__ == '__main__':
    main()
