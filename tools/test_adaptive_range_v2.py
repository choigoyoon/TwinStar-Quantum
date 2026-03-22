#!/usr/bin/env python3
"""2단계 Coarse-to-Fine 백테스트 - v7.27 (신뢰성 개선)

실제 백테스트 결과 기반 파라미터 탐색
- 잘못된 계산 제거
- 명확한 범위 근거
- 결과 저장 기능 추가

Author: Claude Sonnet 4.5
Date: 2026-01-19
"""

import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.parameters import DEFAULT_PARAMS, PARAMETER_SENSITIVITY_WEIGHTS
from config.constants.trading import TOTAL_COST  # ✅ SSOT (v7.27)
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.metrics import calculate_backtest_metrics

# ============ 비용 설정 (SSOT) ============
# TOTAL_COST = 0.0002 (0.02%, config.constants.trading에서 가져옴)
# = SLIPPAGE (0%) + FEE (0.02%)

# ============ 범위 검증 규칙 ============
ALLOWED_FILTER_TF = ['4h', '6h', '8h', '12h', '1d']  # 설계 범위
MIN_ENTRY_VALIDITY = 24  # 최소 대기 시간 (시간)
MAX_ENTRY_VALIDITY = 96  # 최대 대기 시간 (시간)


def build_coarse_ranges() -> Dict[str, List]:
    """Stage 1: Coarse Grid 범위 생성

    근거:
    - filter_tf: ['4h', '6h', '8h', '12h'] - ✅ ALLOWED_FILTER_TF와 일치 (v7.27)
    - entry_validity_hours: [48, 72] - 중장기 대기 (거래 빈도 0.2-0.5/일 목표)
    - atr_mult: [0.9, 1.0, 1.1, 1.25] - 손절 배수 핵심 범위
    - trail_start_r: [0.4, 0.6, 0.8, 1.0] - 트레일링 시작 배수
    - trail_dist_r: [0.03, 0.05, 0.08, 0.1] - 트레일링 간격 (0.03 = v7.26.2 최적값 범위)

    조합 수: 4 × 4 × 2 × 4 × 4 = 512개
    """
    return {
        'atr_mult': [0.9, 1.0, 1.1, 1.25],
        'filter_tf': ['4h', '6h', '8h', '12h'],  # ✅ 8h 추가
        'entry_validity_hours': [48, 72],
        'trail_start_r': [0.4, 0.6, 0.8, 1.0],
        'trail_dist_r': [0.03, 0.05, 0.08, 0.1]
    }


def build_fine_ranges(coarse_optimal: Dict) -> Dict[str, List]:
    """Stage 2: Fine-Tuning 범위 생성

    근거:
    - filter_tf: 중심값 기준 ±2단계 (허용 목록 내에서만)
    - trail_start_r: 중심값 기준 ±30%, 9개 포인트
    - trail_dist_r: 중심값 기준 ±25%, 7개 포인트
    - atr_mult: 중심값 기준 ±15%, 5개 포인트
    - entry_validity_hours: Stage 1 최적값 고정

    조합 수: ~5 × 9 × 7 × 5 × 1 = ~1,575개 (필터 전)
    """
    import numpy as np

    # filter_tf (전후 2단계, 검증)
    weight = PARAMETER_SENSITIVITY_WEIGHTS['filter_tf']
    tf_map = weight['timeframe_order']
    tf_idx = tf_map.index(coarse_optimal['filter_tf'])

    tf_range = []
    for i in range(-2, 3):
        idx = tf_idx + i
        if 0 <= idx < len(tf_map):
            tf = tf_map[idx]
            if tf in ALLOWED_FILTER_TF:
                tf_range.append(tf)

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
    """N개 균등 분할 (소수점 3자리)"""
    if n == 1:
        return [round((min_val + max_val) / 2, 3)]
    step = (max_val - min_val) / (n - 1)
    return [round(min_val + i * step, 3) for i in range(n)]


def validate_param_interaction(params: dict) -> bool:
    """파라미터 상호작용 검증

    규칙:
    1. atr_mult × trail_start_r ∈ [0.5, 2.5]
       - 너무 작으면: 손절 너무 타이트 (노이즈 손절)
       - 너무 크면: 손절 너무 넓음 (큰 손실)

    2. filter_tf vs entry_validity_hours
       - filter_tf='12h' → entry_validity_hours ≤ 24
       - filter_tf='1d' → entry_validity_hours ≤ 48
       (긴 필터 TF는 짧은 대기만 필요)

    3. trail_start_r / trail_dist_r ∈ [3.0, 20.0]
       - 너무 작으면: 트레일링 너무 빨리 시작 (수익 적음)
       - 너무 크면: 트레일링 너무 늦게 시작 (수익 놓침)

    Returns:
        True: 유효 조합
        False: 불조화 조합 (필터링)
    """
    # Rule 1
    interaction_1 = params['atr_mult'] * params['trail_start_r']
    if not (0.5 <= interaction_1 <= 2.5):
        return False

    # Rule 2
    if params['filter_tf'] == '12h' and params['entry_validity_hours'] > 24:
        return False
    if params['filter_tf'] == '1d' and params['entry_validity_hours'] > 48:
        return False

    # Rule 3
    if params['trail_dist_r'] > 0:
        ratio = params['trail_start_r'] / params['trail_dist_r']
        if not (3.0 <= ratio <= 20.0):
            return False

    return True


def run_single_backtest(args: Tuple[pd.DataFrame, dict]) -> Optional[dict]:
    """단일 백테스트 실행

    Args:
        args: (df, params) 튜플

    Returns:
        메트릭 딕셔너리 또는 None (실패 시)
    """
    df, params = args
    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

    try:
        result = strategy.run_backtest(
            df_pattern=df,
            df_entry=df,
            slippage=TOTAL_COST,
            **{k: v for k, v in params.items() if k not in ['slippage', 'fee']}
        )

        # ✅ 타입 검증 (v7.27)
        if isinstance(result, tuple):
            trades = result[0]
        elif isinstance(result, list):
            trades = result
        else:
            # 예상치 못한 타입
            return None

        # ✅ 구조 검증
        if not isinstance(trades, list):
            return None

        if len(trades) < 10:
            return None

        # ✅ 메트릭 계산
        metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

        return {
            'params': params,
            'sharpe': metrics['sharpe_ratio'],
            'win_rate': metrics['win_rate'],
            'mdd': abs(metrics['mdd']),
            'pnl': metrics['total_pnl'],
            'trades': metrics['total_trades'],
            'pf': metrics['profit_factor'],
            'stability': metrics['stability'],
            'avg_pnl': metrics['avg_pnl'],
            'compound_return': metrics['compound_return']
        }

    except Exception as e:
        # ✅ 에러 로깅 (v7.27)
        # 너무 많은 로그 방지를 위해 간단히만 기록
        import logging
        logger = logging.getLogger(__name__)
        param_str = ', '.join(f"{k}={v}" for k, v in list(params.items())[:3])
        logger.debug(f"Backtest failed [{param_str}...]: {str(e)[:80]}")
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

    # Baseline 파라미터
    baseline_params = DEFAULT_PARAMS.copy()
    baseline_params['leverage'] = 1
    baseline_params['macd_fast'] = 6
    baseline_params['macd_slow'] = 18
    baseline_params['macd_signal'] = 7
    # ✅ entry_validity_hours는 범위 탐색으로 결정 (baseline 제거, v7.27)

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

    total_raw = len(combos_raw)
    total_valid = len(combos)
    filter_pct = (filtered_count / total_raw * 100) if total_raw > 0 else 0

    print(f"\nStage 1: Coarse Grid")
    print(f"   전체 조합: {total_raw}개")
    print(f"   필터 제거: {filtered_count}개 ({filter_pct:.1f}%)")
    print(f"   유효 조합: {total_valid}개")
    print(f"   파라미터: {', '.join(keys)}")

    results = []
    completed = 0

    with ProcessPoolExecutor(max_workers=n_cores) as executor:
        tasks = [(df, {**baseline_params, **dict(zip(keys, combo))}) for combo in combos]
        futures = [executor.submit(run_single_backtest, task) for task in tasks]

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

            completed += 1
            if completed % 50 == 0 or completed == total_valid:
                print(f"   진행: {completed}/{total_valid} ({completed/total_valid*100:.0f}%)")

    # Sharpe 기준 정렬
    results.sort(key=lambda x: x['sharpe'], reverse=True)

    print(f"\nStage 1 완료: {len(results)}개 결과")
    print(f"\n상위 5개:")
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. Sharpe={r['sharpe']:.2f}, 승률={r['win_rate']:.1f}%, "
              f"MDD={r['mdd']:.1f}%, 거래={int(r['trades'])}")

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
    # ✅ entry_validity_hours는 범위 탐색으로 결정 (baseline 제거, v7.27)

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
        print(f"\n영역 {region_idx}/5: {region_total}개 조합 (필터: {filtered_count}개 제거)")

        region_results = []
        completed = 0

        with ProcessPoolExecutor(max_workers=n_cores) as executor:
            tasks = [(df, {**baseline_params, **dict(zip(keys, combo))}) for combo in combos]
            futures = [executor.submit(run_single_backtest, task) for task in tasks]

            for future in as_completed(futures):
                result = future.result()
                if result:
                    region_results.append(result)

                completed += 1
                if completed % 50 == 0 or completed == region_total:
                    print(f"   진행: {completed}/{region_total} ({completed/region_total*100:.0f}%)")

        all_results.extend(region_results)
        print(f"  영역 {region_idx} 완료: {len(region_results)}개 결과")

    # Sharpe 기준 정렬
    all_results.sort(key=lambda x: x['sharpe'], reverse=True)

    print(f"\nStage 2 완료: 총 {len(all_results)}개 결과")

    return all_results


def save_results(results: List[dict], output_dir: str = "results") -> str:
    """결과 CSV 저장

    Args:
        results: 백테스트 결과 리스트
        output_dir: 저장 디렉토리

    Returns:
        저장된 파일 경로
    """
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"{output_dir}/coarse_fine_results_{timestamp}.csv"

    # CSV 변환
    rows = []
    for r in results:
        row = {
            'sharpe': r['sharpe'],
            'win_rate': r['win_rate'],
            'mdd': r['mdd'],
            'pnl': r['pnl'],
            'trades': r['trades'],
            'pf': r['pf'],
            'stability': r['stability'],
            'avg_pnl': r['avg_pnl'],
            'compound_return': r['compound_return']
        }
        row.update(r['params'])
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    print(f"\n결과 저장: {filepath}")
    return filepath


def main():
    """메인 함수"""
    print("=" * 100)
    print("2단계 Coarse-to-Fine 백테스트 - v7.27 (신뢰성 개선)")
    print("   비용: 슬리피지 0% + 수수료 0.02% (SSOT)")
    print("   Stage 1: 512개 조합 (4×4×2×4×4), Stage 2: ~1,575개 조합/영역")
    print("   ✅ 개선: SSOT 준수, 8h 필터 추가, 타입 검증, 에러 로깅")
    print("=" * 100)

    # 데이터 로드
    print("\n데이터 로딩...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    success = dm.load_historical()
    if not success or dm.df_entry_full is None or len(dm.df_entry_full) == 0:
        print("ERROR: 데이터 로드 실패")
        return

    # 15분봉 → 1시간봉 리샘플링 (v7.26.2와 동일)
    df_15m = dm.df_entry_full.copy()

    if 'timestamp' not in df_15m.columns:
        df_15m.reset_index(inplace=True)

    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_temp = df_15m.set_index('timestamp')

    df = df_temp.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    df.reset_index(inplace=True)

    # 2020-01-01 이후 필터링
    df = df[df['timestamp'] >= '2020-01-01'].copy()

    print(f"OK 데이터:")
    print(f"   15분봉: {len(df_15m):,}개")
    print(f"   1시간봉: {len(df):,}개 (2020년 이후)")

    start_date = df['timestamp'].iloc[0]
    end_date = df['timestamp'].iloc[-1]
    total_days = (end_date - start_date).days
    print(f"   기간: {start_date} ~ {end_date}")
    print(f"   일수: {total_days:,}일")

    # Stage 1: Coarse Grid
    start_total = datetime.now()
    top_5 = run_stage_1_parallel(df, n_cores=8)

    if len(top_5) < 5:
        print(f"WARNING: Stage 1 결과가 5개 미만입니다 ({len(top_5)}개)")
        return

    # Stage 2: Fine-Tuning
    final_results = run_stage_2_parallel(df, top_5[:5], n_cores=8)

    elapsed_total = (datetime.now() - start_total).total_seconds()

    # 결과 저장
    save_results(final_results)

    # 상위 15개 출력
    print("\n" + "=" * 110)
    print("상위 15개 결과 (Sharpe 순)")
    print("=" * 110)
    print(f"{'순위':>4} {'등급':>4} {'Sharpe':>8} {'승률':>7} {'MDD':>7} {'PnL':>9} "
          f"{'거래':>6} {'PF':>6} {'건당':>6} 파라미터")
    print("-" * 110)

    for i, r in enumerate(final_results[:15], 1):
        params_str = ', '.join(f"{k}={v}" for k, v in sorted(r['params'].items()))
        print(f"{i:>4} {r['stability']:>4} {r['sharpe']:>8.2f} {r['win_rate']:>6.1f}% "
              f"{r['mdd']:>6.1f}% {r['pnl']:>8.1f}% {int(r['trades']):>6} "
              f"{r['pf']:>6.2f} {r['avg_pnl']:>5.2f}% {params_str}")

    # 최적 조합
    best = final_results[0]
    print("\n" + "=" * 70)
    print("최적 조합 (v7.27)")
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
    print(f"MDD: {best['mdd']:.1f}% | PnL: {best['pnl']:.1f}% | 거래: {int(best['trades'])}회")
    print(f"PF: {best['pf']:.2f} | 건당: {best['avg_pnl']:.2f}% | 안전 레버리지: {safe_lev:.1f}x")

    print(f"\n총 소요 시간: {elapsed_total:.1f}초 ({elapsed_total/60:.1f}분)")
    print("\n완료!")


if __name__ == '__main__':
    main()
