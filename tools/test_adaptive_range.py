#!/usr/bin/env python3
"""2단계 Coarse-to-Fine 백테스트 - v7.26

민감도 기반 Fine-Tuning + 파라미터 상호작용 검증

Stage 1: Coarse Grid (~1,840개 조합)
  - filter_tf: 4개 ('12h' 추가)
  - entry_validity_hours: 3개 (6, 24, 48)
  - 상호작용 필터: 15% 제거

Stage 2: Fine-Tuning (상위 5개 영역별 ~1,340개 조합)
  - 민감도 기반 범위: filter_tf (±2단계), trail_start_r (±30%, 9개)
  - 상호작용 필터 적용

Author: Claude Sonnet 4.5
Date: 2026-01-19
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed

# 프로젝트 루트 및 tools 디렉토리 추가
project_root = Path(__file__).parent.parent
tools_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(tools_dir))

from config.parameters import DEFAULT_PARAMS, PARAMETER_SENSITIVITY_WEIGHTS
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.metrics import calculate_backtest_metrics

# adaptive_range_builder 함수 직접 정의 (import 문제 회피)
def build_coarse_ranges() -> Dict[str, List]:
    """Coarse Grid 범위 생성 (Stage 1) - v7.26.2 최종 범위

    변경 (v7.26.1 → v7.26.2):
    - entry_validity_hours: [24, 48] → [48, 72]
      (24 제거, 거래 빈도 대폭 감소 목표)
    - trail_dist_r: [0.03, 0.05, 0.08, 0.1] → [0.05, 0.08, 0.1]
      (0.03 제거, 너무 타이트한 트레일링 제거)

    조합: 384 → 288개 (-25%)
    실행 시간: 4분 → 3분 (-25%)
    예상 거래: 2,000-3,000회 (v7.26.1 대비 -67%)
    """
    return {
        'atr_mult': [0.9, 1.0, 1.1, 1.25],          # 4개
        'filter_tf': ['4h', '6h', '12h'],            # 3개
        'entry_validity_hours': [48, 72],            # 2개 ← 24 제거!
        'trail_start_r': [0.4, 0.6, 0.8, 1.0],      # 4개
        'trail_dist_r': [0.05, 0.08, 0.1]           # 3개 ← 0.03 제거!
    }
    # 4 × 3 × 2 × 4 × 3 = 288개

def build_fine_ranges(coarse_optimal: Dict) -> Dict[str, List]:
    """Fine-Tuning 범위 생성 (Stage 2) - v7.26.1 범위 검증 추가

    변경:
    - filter_tf 범위 확장 시 허용 목록 검증 추가
    - '2h', '3h' 등 설계 범위 밖 파라미터 자동 필터링

    조합: 5 × 9 × 7 × 5 × 1 = 1,575개 (기존 1,029 → +53%)
    """
    import numpy as np

    # ✅ 허용된 filter_tf 목록 (설계 범위)
    ALLOWED_FILTER_TF = ['4h', '6h', '8h', '12h', '1d']

    # filter_tf (전후 2단계 + 검증)
    weight = PARAMETER_SENSITIVITY_WEIGHTS['filter_tf']
    tf_map = weight['timeframe_order']
    tf_idx = tf_map.index(coarse_optimal['filter_tf'])

    tf_range = []
    for i in range(-2, 3):  # 전후 2단계
        idx = tf_idx + i
        if 0 <= idx < len(tf_map):
            tf = tf_map[idx]
            if tf in ALLOWED_FILTER_TF:  # ← 검증 추가!
                tf_range.append(tf)

    # 최소 1개 보장 (모두 필터링되면 중심값 사용)
    if not tf_range:
        tf_range = [coarse_optimal['filter_tf']]

    # trail_start_r (±30%, 9개)
    ts_weight = PARAMETER_SENSITIVITY_WEIGHTS['trail_start_r']
    ts_center = coarse_optimal['trail_start_r']
    ts_min = max(ts_weight['min_value'], ts_center * 0.7)
    ts_max = min(ts_weight['max_value'], ts_center * 1.3)
    ts_range = _linspace_n(ts_min, ts_max, ts_weight['n_points'])

    # trail_dist_r (±25%, 7개)
    td_weight = PARAMETER_SENSITIVITY_WEIGHTS['trail_dist_r']
    td_center = coarse_optimal['trail_dist_r']
    td_min = max(td_weight['min_value'], td_center * 0.75)
    td_max = min(td_weight['max_value'], td_center * 1.25)
    td_range = _linspace_n(td_min, td_max, td_weight['n_points'])

    # atr_mult (±15%, 5개)
    atr_weight = PARAMETER_SENSITIVITY_WEIGHTS['atr_mult']
    atr_center = coarse_optimal['atr_mult']
    atr_min = max(atr_weight['min_value'], atr_center * 0.85)
    atr_max = min(atr_weight['max_value'], atr_center * 1.15)
    atr_range = _linspace_n(atr_min, atr_max, atr_weight['n_points'])

    return {
        'filter_tf': tf_range,
        'trail_start_r': ts_range,
        'trail_dist_r': td_range,
        'atr_mult': atr_range,
        'entry_validity_hours': [coarse_optimal['entry_validity_hours']]
    }


def _linspace_n(min_val: float, max_val: float, n: int) -> List[float]:
    """N개 균등 분할"""
    if n == 1:
        return [round((min_val + max_val) / 2, 3)]
    step = (max_val - min_val) / (n - 1)
    return [round(min_val + i * step, 3) for i in range(n)]

# ============ 비용 설정 ============
SLIPPAGE = 0.0       # 0% 슬리피지 (지정가)
FEE = 0.0002         # 0.02% 메이커 수수료
TOTAL_COST = SLIPPAGE + FEE


def validate_param_interaction(params: dict) -> bool:
    """파라미터 상호작용 검증

    Returns:
        True: 유효 조합
        False: 불조화 조합 (필터링)
    """
    # Rule 1: atr_mult × trail_start_r
    interaction_1 = params['atr_mult'] * params['trail_start_r']
    if not (0.5 <= interaction_1 <= 2.5):
        return False

    # Rule 2: filter_tf vs entry_validity_hours
    if params['filter_tf'] == '12h' and params['entry_validity_hours'] > 24:
        return False
    if params['filter_tf'] == '1d' and params['entry_validity_hours'] > 48:
        return False

    # Rule 3: trail_start_r / trail_dist_r
    if params['trail_dist_r'] > 0:
        ratio = params['trail_start_r'] / params['trail_dist_r']
        if not (3.0 <= ratio <= 20.0):
            return False

    return True


def run_single_backtest(args):
    """단일 백테스트 실행 (Fine-Tuning Quick과 동일)

    Args:
        args: (df, params) 튜플

    Returns:
        메트릭 딕셔너리 또는 None
    """
    df, params = args
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

    except Exception:
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

    # 조합 생성 + 검증
    keys = list(coarse_ranges.keys())
    values = [coarse_ranges[k] for k in keys]
    combos_raw = list(product(*values))

    combos = []
    filtered_count = 0

    for combo in combos_raw:
        params_dict = dict(zip(keys, combo))
        if validate_param_interaction(params_dict):
            combos.append(combo)
        else:
            filtered_count += 1

    print(f"\nStage 1: Coarse Grid ({len(combos_raw)}개 조합)")
    print(f"   상호작용 필터: {filtered_count}개 제거 ({filtered_count/len(combos_raw)*100:.1f}%)")

    total = len(combos)
    print(f"   유효 조합: {total}개")
    print(f"파라미터: {', '.join(keys)}")

    results = []
    completed = 0

    with ProcessPoolExecutor(max_workers=n_cores) as executor:
        # 인자를 튜플로 전달
        tasks = [(df, {**baseline_params, **dict(zip(keys, combo))}) for combo in combos]
        futures = [executor.submit(run_single_backtest, task) for task in tasks]

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

            completed += 1
            # 2,160개 조합: 50개마다 출력 (43번 출력)
            if completed % 50 == 0 or completed == total:
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

        # 조합 생성 + 검증
        keys = list(fine_ranges.keys())
        values = [fine_ranges[k] for k in keys]
        combos_raw = list(product(*values))

        combos = []
        filtered_count = 0

        for combo in combos_raw:
            params_dict = dict(zip(keys, combo))
            if validate_param_interaction(params_dict):
                combos.append(combo)
            else:
                filtered_count += 1

        region_total = len(combos)
        print(f"\n영역 {region_idx}/5: {region_total}개 조합 탐색 중 (필터: {filtered_count}개 제거)...")

        region_results = []
        completed = 0

        with ProcessPoolExecutor(max_workers=n_cores) as executor:
            # 인자를 튜플로 전달
            tasks = [(df, {**baseline_params, **dict(zip(keys, combo))}) for combo in combos]
            futures = [executor.submit(run_single_backtest, task) for task in tasks]

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
    print("2단계 Coarse-to-Fine 백테스트 - v7.26.2")
    print("   비용: 슬리피지 0% + 수수료 0.02%")
    print("   Stage 1: 288개 조합 (entry_validity_hours=48,72), Stage 2: ~1,440개 조합")
    print("=" * 100)

    # 데이터 로드
    print("\n데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    success = dm.load_historical()
    if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
        print("ERROR: 데이터 로드 실패")
        return

    # 2020년 이후 전체 데이터 사용
    df = dm.df_entry_full.copy()

    # 2020-01-01 이후 필터링
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'] >= '2020-01-01'].copy()

    print(f"OK 데이터: {len(df):,}개 1시간봉 (2020년 이후)")
    if 'timestamp' in df.columns:
        print(f"   기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

    # Stage 1: Coarse Grid (병렬)
    start_total = datetime.now()
    top_5 = run_stage_1_parallel(df, n_cores=8)

    if len(top_5) < 5:
        print(f"WARNING: Stage 1 결과가 5개 미만입니다 ({len(top_5)}개)")
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
    print("최적 조합 (v7.26.2)")
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

    print(f"\n총 소요 시간: {elapsed_total:.1f}초 ({elapsed_total/60:.1f}분)")
    print("\n완료!")


if __name__ == '__main__':
    main()
