#!/usr/bin/env python3
"""ADX+DI 필터 빠른 테스트 (v7.25)

MACD 최적 파라미터 + ADX 필터 조합 테스트

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

# ============ v7.25 최적 파라미터 (Fine-Tuning 결과) ============
OPTIMAL_BASE = {
    'atr_mult': 1.25,
    'filter_tf': '4h',
    'trail_start_r': 0.4,
    'trail_dist_r': 0.05,
}

# ============ ADX 테스트 범위 ============
ADX_RANGES = {
    'use_adx_filter': [False, True],          # 2개 (ADX 없음 vs 있음)
    'adx_threshold': [20, 25, 30, 35],        # 4개 (Wilder 표준: 25)
    'adx_period': [14],                       # 1개 (Wilder 표준)
}
# 총 조합: 2 * 4 * 1 = 8개
# (use_adx_filter=False일 때 adx_threshold/period는 무시되므로 실제 유효: 5개)

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
    # Windows 콘솔 UTF-8 인코딩 설정
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("🔬 ADX+DI 필터 Quick Test (v7.25)")
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

    print(f"\n📋 테스트 조합:")
    print(f"   1. ADX 없음 (Baseline)")
    print(f"   2. ADX 임계값: {ADX_RANGES['adx_threshold']}")
    print(f"   3. ADX 주기: {ADX_RANGES['adx_period'][0]} (Wilder 표준)")

    # 테스트 1: ADX 없음 (Baseline)
    print(f"\n{'='*80}")
    print("📊 [1/5] ADX 없음 (Baseline)")
    print(f"{'='*80}")

    test_params = baseline_params.copy()
    test_params['use_adx_filter'] = False

    m = run_backtest(df, test_params)

    sharpe = m.get('sharpe_ratio', 0)
    win_rate = m.get('win_rate', 0)
    mdd = abs(m.get('mdd', 100))
    pnl = m.get('total_pnl', 0)
    trades = m.get('total_trades', 0) or m.get('trade_count', 0)
    pf = m.get('profit_factor', 0)
    grade = get_grade(sharpe, win_rate, mdd, pf)

    results.append({
        'adx_enabled': False,
        'adx_threshold': None,
        'adx_period': None,
        'sharpe': sharpe,
        'win_rate': win_rate,
        'mdd': mdd,
        'pnl': pnl,
        'trades': trades,
        'pf': pf,
        'grade': grade,
    })

    print(f"   등급: {grade} | Sharpe: {sharpe:.2f} | 승률: {win_rate:.1f}%")
    print(f"   MDD: {mdd:.1f}% | PnL: {pnl:.1f}% | 거래: {trades}회 | PF: {pf:.2f}")

    # 테스트 2-5: ADX 임계값별
    for i, threshold in enumerate(ADX_RANGES['adx_threshold'], 2):
        print(f"\n{'='*80}")
        print(f"🔍 [{i}/5] ADX 임계값 {threshold} (ADX > {threshold} 필터)")
        print(f"{'='*80}")

        test_params = baseline_params.copy()
        test_params['use_adx_filter'] = True
        test_params['adx_threshold'] = threshold
        test_params['adx_period'] = ADX_RANGES['adx_period'][0]

        m = run_backtest(df, test_params)

        sharpe = m.get('sharpe_ratio', 0)
        win_rate = m.get('win_rate', 0)
        mdd = abs(m.get('mdd', 100))
        pnl = m.get('total_pnl', 0)
        trades = m.get('total_trades', 0) or m.get('trade_count', 0)
        pf = m.get('profit_factor', 0)
        grade = get_grade(sharpe, win_rate, mdd, pf)

        results.append({
            'adx_enabled': True,
            'adx_threshold': threshold,
            'adx_period': ADX_RANGES['adx_period'][0],
            'sharpe': sharpe,
            'win_rate': win_rate,
            'mdd': mdd,
            'pnl': pnl,
            'trades': trades,
            'pf': pf,
            'grade': grade,
        })

        print(f"   등급: {grade} | Sharpe: {sharpe:.2f} | 승률: {win_rate:.1f}%")
        print(f"   MDD: {mdd:.1f}% | PnL: {pnl:.1f}% | 거래: {trades}회 | PF: {pf:.2f}")

    elapsed = (datetime.now() - start).total_seconds()

    # 정렬 (Sharpe 기준)
    results.sort(key=lambda x: x['sharpe'], reverse=True)

    # 결과 테이블
    print("\n" + "=" * 95)
    print("🏆 전체 결과 (Sharpe 순)")
    print("=" * 95)
    print(f"{'순위':>4} {'등급':>4} {'ADX':>5} {'임계값':>6} {'Sharpe':>8} {'승률':>8} {'MDD':>8} {'PnL':>10} {'거래':>6} {'PF':>6}")
    print("-" * 95)

    for i, r in enumerate(results, 1):
        emoji = {'S': '🏆', 'A': '🥇', 'B': '🥈', 'C': '🥉', 'F': '❌'}.get(r['grade'], '?')
        adx_str = '없음' if not r['adx_enabled'] else f">{r['adx_threshold']}"
        threshold_str = '-' if not r['adx_enabled'] else str(r['adx_threshold'])

        print(f"{i:>4} {emoji}{r['grade']:>3} {adx_str:>5} {threshold_str:>6} {r['sharpe']:>8.2f} "
              f"{r['win_rate']:>7.1f}% {r['mdd']:>7.1f}% {r['pnl']:>9.1f}% {r['trades']:>6} {r['pf']:>6.2f}")

    # 최적 조합
    best = results[0]
    baseline = results[[i for i, r in enumerate(results) if not r['adx_enabled']][0]]

    print("\n" + "=" * 80)
    print("🎯 최적 조합")
    print("=" * 80)

    if best['adx_enabled']:
        print("✅ ADX 필터 포함 (성능 향상)")
        print(f"\n```python")
        print("OPTIMAL_PARAMS = {")
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
        print("OPTIMAL_PARAMS = {")
        print(f"    'atr_mult': {OPTIMAL_BASE['atr_mult']},")
        print(f"    'filter_tf': '{OPTIMAL_BASE['filter_tf']}',")
        print(f"    'trail_start_r': {OPTIMAL_BASE['trail_start_r']},")
        print(f"    'trail_dist_r': {OPTIMAL_BASE['trail_dist_r']},")
        print(f"    'use_adx_filter': False,  # ADX 제외")
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

        # 판정 (MDD는 낮을수록 좋음, 거래수는 중립)
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
    trades_diff_pct = (best['trades'] - baseline['trades']) / baseline['trades'] * 100

    print("\n" + "=" * 80)
    print("💡 결론 및 권장사항")
    print("=" * 80)

    if sharpe_diff_pct >= 5:
        print("✅ 시나리오 1: ADX 필터가 성능을 크게 향상시킴")
        print(f"   - Sharpe Ratio +{sharpe_diff_pct:.1f}% (임계값: +5%)")
        print(f"   - 조치: ADX 필터를 최종 파라미터에 포함 권장")
    elif sharpe_diff_pct >= 1:
        print("⚠️ 시나리오 2: ADX 필터가 성능을 약간 향상")
        print(f"   - Sharpe Ratio +{sharpe_diff_pct:.1f}% (임계값: +1~5%)")
        print(f"   - 조치: 선택 사항 (복잡도 증가 vs 성능 향상 trade-off)")
    elif sharpe_diff_pct >= -1:
        print("➖ 시나리오 3: ADX 필터 영향 미미 (중복 필터)")
        print(f"   - Sharpe Ratio {sharpe_diff_pct:+.1f}% (임계값: -1~+1%)")
        print(f"   - 이유: filter_tf='4h'가 이미 추세 필터 역할 충분")
        print(f"   - 조치: ADX 제외 권장 (복잡도 증가 대비 이득 없음)")
    else:
        print("❌ 시나리오 4: ADX 필터가 성능 저하")
        print(f"   - Sharpe Ratio {sharpe_diff_pct:.1f}% (임계값: <-1%)")
        print(f"   - 이유: 좋은 신호도 과도하게 필터링")
        print(f"   - 조치: ADX 제외 필수")

    if abs(trades_diff_pct) >= 20:
        print(f"\n⚠️ 거래 빈도 영향:")
        print(f"   - 거래수 {trades_diff_pct:+.1f}% 변화")
        if trades_diff_pct < -20:
            print(f"   - 거래 기회 과도하게 감소 → 샘플 부족 위험")

    # 결과 저장
    import json
    report_dir = project_root / 'reports' / 'adx_test'
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = report_dir / f'adx_quick_{ts}.json'

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'version': 'v7.25_adx',
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
                    'use_adx_filter': best['adx_enabled'],
                    'adx_threshold': best['adx_threshold'],
                    'adx_period': best['adx_period'],
                } if best['adx_enabled'] else {**OPTIMAL_BASE, 'use_adx_filter': False},
                'sharpe': float(best['sharpe']),
                'win_rate': float(best['win_rate']),
                'mdd': float(best['mdd']),
                'pnl': float(best['pnl']),
                'trades': int(best['trades']),
                'pf': float(best['pf']),
                'grade': best['grade'],
            },
            'all_results': [
                {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v)
                 for k, v in r.items()}
                for r in results
            ],
            'sharpe_diff_pct': float(sharpe_diff_pct),
            'trades_diff_pct': float(trades_diff_pct),
            'elapsed_seconds': elapsed,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 저장: {json_path}")
    print(f"⏱️ 소요: {elapsed:.1f}초")
    print("\n✅ 완료!")


if __name__ == '__main__':
    main()
