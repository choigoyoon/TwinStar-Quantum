#!/usr/bin/env python3
"""2단계 Coarse-to-Fine 백테스트 - v7.25.11

Fine-Tuning Quick 방식 기반 (BacktestOptimizer 미사용)

Stage 1: Coarse Grid (540개 조합 - 5배 확장)
Stage 2: Fine-Tuning (상위 5개 영역별 ~1,029개 조합 - 정밀도 2배)

Author: Claude Sonnet 4.5
Date: 2026-01-19
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.parameters import DEFAULT_PARAMS
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.metrics import calculate_backtest_metrics
from tools.adaptive_range_builder import build_coarse_ranges, build_fine_ranges

# ============ 비용 설정 ============
SLIPPAGE = 0.0       # 0% 슬리피지 (지정가)
FEE = 0.0002         # 0.02% 메이커 수수료
TOTAL_COST = SLIPPAGE + FEE


def run_single_backtest(df: pd.DataFrame, params: dict) -> Optional[dict]:
    """단일 백테스트 실행 (Fine-Tuning Quick과 동일)

    Args:
        df: 1시간봉 DataFrame
        params: 파라미터 딕셔너리

    Returns:
        메트릭 딕셔너리 또는 None
    """
    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

    try:
        trades = strategy.run_backtest(
            df_pattern=df,  # ← 1h 봉 그대로!
            df_entry=df,
            slippage=TOTAL_COST,
            **{k: v for k, v in params.items() if k not in ['slippage', 'fee']}
        )

        if isinstance(trades, tuple):
            trades = trades[0]

        if not trades or len(trades) < 10:
            return None

        metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

        return {
            'params': params,
            'sharpe': metrics['sharpe_ratio'],
            'win_rate': metrics['win_rate'],
            'mdd': abs(metrics['mdd']),
            'pnl': metrics['total_pnl'],
            'trades': metrics['total_trades'],
            'pf': metrics['profit_factor'],
            'stability': metrics['stability']
        }

    except Exception as e:
        print(f"⚠️ 백테스트 에러: {e}")
        return None


def run_stage_1_parallel(df: pd.DataFrame, n_cores: int = 8) -> List[dict]:
    """Stage 1: Coarse Grid 병렬 실행

    Args:
        df: 1시간봉 DataFrame
        n_cores: 워커 수

    Returns:
        결과 리스트 (Sharpe 정렬)
    """
    coarse_ranges = build_coarse_ranges()

    # Baseline 파라미터 (Fine-Tuning Quick과 동일)
    baseline_params = DEFAULT_PARAMS.copy()
    baseline_params['leverage'] = 1
    baseline_params['macd_fast'] = 6
    baseline_params['macd_slow'] = 18
    baseline_params['macd_signal'] = 7
    baseline_params['entry_validity_hours'] = 6.0

    # 조합 생성
    keys = list(coarse_ranges.keys())
    values = [coarse_ranges[k] for k in keys]
    combos = list(product(*values))

    total = len(combos)
    print(f"\nStage 1: Coarse Grid ({total}개 조합)")
    print(f"파라미터: {', '.join(keys)}")

    results = []
    completed = 0

    with ProcessPoolExecutor(max_workers=n_cores) as executor:
        futures = []

        for combo in combos:
            params = baseline_params.copy()
            params.update(dict(zip(keys, combo)))
            futures.append(executor.submit(run_single_backtest, df, params))

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

            completed += 1
            # 540개 조합: 10개마다 출력 (54번 출력)
            if completed % 10 == 0 or completed == total:
                print(f"   진행: {completed}/{total} ({completed/total*100:.0f}%)")

    # Sharpe 기준 정렬
    results.sort(key=lambda x: x['sharpe'], reverse=True)

    print(f"\nStage 1 완료: {len(results)}개 결과")
    print(f"\n상위 5개 최적 영역:")
    for i, r in enumerate(results[:5], 1):
        params_str = ', '.join(f"{k}={v}" for k, v in sorted(r['params'].items()) if k in keys)
        print(f"  {i}. Sharpe={r['sharpe']:.2f}, MDD={r['mdd']:.1f}%, trades={int(r['trades'])}, {params_str}")

    return results


def run_stage_2_parallel(df: pd.DataFrame, top_5: List[dict], n_cores: int = 8) -> List[dict]:
    """Stage 2: Fine-Tuning 병렬 실행

    Args:
        df: 1시간봉 DataFrame
        top_5: Stage 1 상위 5개 결과
        n_cores: 워커 수

    Returns:
        전체 결과 리스트 (Sharpe 정렬)
    """
    all_results = []

    # Baseline 파라미터
    baseline_params = DEFAULT_PARAMS.copy()
    baseline_params['leverage'] = 1
    baseline_params['macd_fast'] = 6
    baseline_params['macd_slow'] = 18
    baseline_params['macd_signal'] = 7
    baseline_params['entry_validity_hours'] = 6.0

    print(f"\nStage 2: Fine-Tuning (상위 5개 영역)")

    for region_idx, coarse_result in enumerate(top_5, 1):
        fine_ranges = build_fine_ranges(coarse_result['params'])

        # 조합 생성
        keys = list(fine_ranges.keys())
        values = [fine_ranges[k] for k in keys]
        combos = list(product(*values))

        region_total = len(combos)
        print(f"\n영역 {region_idx}/5: {region_total}개 조합 탐색 중...")

        region_results = []
        completed = 0

        with ProcessPoolExecutor(max_workers=n_cores) as executor:
            futures = []

            for combo in combos:
                params = baseline_params.copy()
                params.update(dict(zip(keys, combo)))
                futures.append(executor.submit(run_single_backtest, df, params))

            for future in as_completed(futures):
                result = future.result()
                if result:
                    region_results.append(result)

                completed += 1
                # 1,029개 조합: 50개마다 출력 (20번 출력)
                if completed % 50 == 0 or completed == region_total:
                    print(f"     진행: {completed}/{region_total} ({completed/region_total*100:.0f}%)")

        all_results.extend(region_results)
        print(f"  영역 {region_idx} 완료: {len(region_results)}개 결과")

    # Sharpe 기준 정렬
    all_results.sort(key=lambda x: x['sharpe'], reverse=True)

    print(f"\nStage 2 완료: 총 {len(all_results)}개 조합")

    return all_results


def main():
    """메인 함수"""
    print("=" * 100)
    print("2단계 Coarse-to-Fine 백테스트 - v7.25.11")
    print("   비용: 슬리피지 0% + 수수료 0.02%")
    print("   Stage 1: 540개 조합 (5배 확장), Stage 2: ~5,145개 조합 (정밀도 2배)")
    print("=" * 100)

    # 데이터 로드
    print("\n데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    success = dm.load_historical()
    if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
        print("❌ 데이터 로드 실패")
        return

    # 2020년 이후 전체 데이터 사용
    df = dm.df_entry_full.copy()

    # 2020-01-01 이후 필터링
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'] >= '2020-01-01'].copy()

    print(f"✅ 데이터: {len(df):,}개 1시간봉 (2020년 이후)")
    if 'timestamp' in df.columns:
        print(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

    # Stage 1: Coarse Grid (병렬)
    start_total = datetime.now()
    top_5 = run_stage_1_parallel(df, n_cores=8)

    if len(top_5) < 5:
        print(f"⚠️ Stage 1 결과가 5개 미만입니다 ({len(top_5)}개)")
        return

    # Stage 2: Fine-Tuning (병렬)
    final_results = run_stage_2_parallel(df, top_5[:5], n_cores=8)

    elapsed_total = (datetime.now() - start_total).total_seconds()

    # 상위 15개 결과 출력 (Fine-Tuning Quick과 동일)
    print("\n" + "=" * 100)
    print("상위 15개 결과 (Sharpe 순)")
    print("=" * 100)
    print(f"{'순위':>4} {'등급':>4} {'Sharpe':>8} {'승률':>8} {'MDD':>8} {'PnL':>10} {'거래':>6} {'PF':>6} 파라미터")
    print("-" * 100)

    for i, r in enumerate(final_results[:15], 1):
        params_str = ', '.join(f"{k}={v}" for k, v in sorted(r['params'].items()))
        print(f"{i:>4} {r['stability']:>4} {r['sharpe']:>8.2f} {r['win_rate']:>7.1f}% {r['mdd']:>7.1f}% "
              f"{r['pnl']:>9.1f}% {int(r['trades']):>6} {r['pf']:>6.2f} {params_str}")

    # 최적 조합
    best = final_results[0]
    print("\n" + "=" * 70)
    print("최적 조합 (v7.25.11)")
    print("=" * 70)
    print("```python")
    print("OPTIMAL_PARAMS = {")
    for k in ['atr_mult', 'filter_tf', 'entry_validity_hours', 'trail_start_r', 'trail_dist_r']:
        v = best['params'][k]
        if isinstance(v, str):
            print(f"    '{k}': '{v}',")
        else:
            print(f"    '{k}': {v},")
    print("}")
    print("```")

    safe_lev = 10.0 / best['mdd'] if best['mdd'] > 0 else 1.0
    safe_lev = min(safe_lev, 20.0)

    print(f"\n등급: {best['stability']} | Sharpe: {best['sharpe']:.2f} | 승률: {best['win_rate']:.1f}%")
    print(f"MDD: {best['mdd']:.1f}% | PnL: {best['pnl']:.1f}% | 거래: {int(best['trades'])}회 | PF: {best['pf']:.2f}")
    print(f"안전 레버리지: {safe_lev:.1f}x")

    print(f"\n⏱️ 총 소요 시간: {elapsed_total:.1f}초 ({elapsed_total/60:.1f}분)")
    print("\n✅ 완료!")


if __name__ == '__main__':
    main()
