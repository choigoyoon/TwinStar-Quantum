"""
지표 민감도 분석 도구
====================

각 지표 파라미터가 백테스트 결과에 미치는 영향을 분석하여
퀵/스탠다드/딥 모드의 탐색 범위를 결정합니다.

분석 방법:
1. 각 지표를 넓은 범위로 딥 모드 탐색
2. 파라미터 값에 따른 성과 변화 분석
3. 민감도가 높은 지표 = 퀵 모드에서도 다양하게 탐색
4. 민감도가 낮은 지표 = 퀸 모드에서 고정값 사용
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import time
from collections import defaultdict
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from core.optimizer import BacktestOptimizer
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


# ==================== CPU 워커 자동 계산 ====================

def get_optimal_workers(mode: str = 'standard') -> int:
    """
    최적 워커 수 자동 계산 (환경 독립적)

    Args:
        mode: 'quick', 'standard', 'deep'

    Returns:
        워커 수 (1 ~ cpu_count)

    Examples:
        2코어: quick=1, standard=1, deep=1
        4코어: quick=2, standard=3, deep=3
        8코어: quick=4, standard=6, deep=7
        16코어: quick=8, standard=12, deep=15
    """
    total_cores = mp.cpu_count()

    if total_cores is None or total_cores <= 0:
        return 1

    if mode == 'quick':
        return max(1, total_cores // 2)
    elif mode == 'deep':
        return max(1, total_cores - 1)
    else:  # standard
        return max(1, int(total_cores * 0.75))


def get_worker_info(mode: str = 'standard') -> dict:
    """
    워커 정보 반환 (로깅/GUI 표시용)

    Returns:
        {
            'total_cores': int,
            'workers': int,
            'usage_percent': float,
            'description': str,
            'free_cores': int
        }
    """
    total = mp.cpu_count() or 1
    workers = get_optimal_workers(mode)
    usage = (workers / total) * 100

    descriptions = {
        'quick': f'빠른 모드 (코어 {usage:.0f}% 사용)',
        'standard': f'표준 모드 (코어 {usage:.0f}% 사용)',
        'deep': f'딥 모드 (코어 {usage:.0f}% 사용, 최대 성능)',
    }

    return {
        'total_cores': total,
        'workers': workers,
        'usage_percent': usage,
        'description': descriptions.get(mode, '알 수 없음'),
        'free_cores': total - workers,
    }


# ==================== 딥 모드 탐색 범위 ====================

DEEP_SEARCH_RANGES = {
    # MACD
    'macd_fast': list(range(5, 15)),           # 10개 (5~14)
    'macd_slow': list(range(16, 35, 2)),       # 10개 (16,18,20...34)
    'macd_signal': list(range(5, 14)),         # 9개 (5~13)

    # ADX
    'adx_period': [8, 10, 12, 14, 16, 18, 20, 25, 30],  # 9개
    'adx_threshold': [15, 18, 20, 22, 25, 28, 30, 35],  # 8개

    # EMA
    'ema_period': [8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100],  # 12개

    # ATR
    'atr_mult': [0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0],  # 10개
    'atr_period': [5, 7, 10, 14, 18, 21, 25, 30],  # 8개

    # RSI
    'rsi_period': [5, 7, 9, 11, 14, 17, 21, 25, 30],  # 9개
    'pullback_rsi_long': [30, 35, 40, 45, 50],   # 5개
    'pullback_rsi_short': [50, 55, 60, 65, 70],  # 5개

    # 트레일링 스탑
    'trail_start_r': [0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0],  # 9개
    'trail_dist_r': [0.1, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8],  # 9개
}


def analyze_single_parameter(
    symbol: str,
    param_name: str,
    param_values: List,
    base_params: Dict,
    df_pattern: pd.DataFrame,
    df_entry: pd.DataFrame
) -> pd.DataFrame:
    """
    단일 파라미터의 민감도 분석

    Args:
        symbol: 심볼
        param_name: 파라미터 이름
        param_values: 테스트할 값 리스트
        base_params: 기본 파라미터 (고정값)
        df: OHLCV 데이터

    Returns:
        결과 DataFrame (param_value, win_rate, return, mdd, sharpe, trades)
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"파라미터 분석: {param_name}")
    logger.info(f"테스트 범위: {param_values}")
    logger.info(f"{'='*60}")

    results = []

    for value in param_values:
        # 파라미터 설정
        test_params = base_params.copy()
        test_params[param_name] = value

        # 백테스트 실행
        try:
            from utils.metrics import calculate_backtest_metrics

            strategy = AlphaX7Core()
            trades = strategy.run_backtest(df_pattern, df_entry, **test_params)

            # trades 리스트에서 metrics 계산
            if isinstance(trades, list):
                metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)
            else:
                # 이미 dict인 경우 (다른 전략에서)
                metrics = trades

            results.append({
                'param_value': value,
                'win_rate': metrics.get('win_rate', 0),
                'total_return': metrics.get('total_pnl', 0),  # 'total_return' → 'total_pnl'
                'mdd': metrics.get('mdd', 0),  # 'max_drawdown' → 'mdd'
                'sharpe': metrics.get('sharpe_ratio', 0),
                'trades': metrics.get('total_trades', 0),
                'profit_factor': metrics.get('profit_factor', 0),
            })

            logger.info(
                f"{param_name}={value:6} → "
                f"승률 {metrics.get('win_rate', 0):5.1f}% | "
                f"수익 {metrics.get('total_pnl', 0):7.2f}% | "
                f"MDD {metrics.get('mdd', 0):5.2f}% | "
                f"거래 {metrics.get('total_trades', 0):4}회"
            )

        except Exception as e:
            logger.error(f"{param_name}={value} 테스트 실패: {e}")
            results.append({
                'param_value': value,
                'win_rate': 0,
                'total_return': 0,
                'mdd': 100,
                'sharpe': 0,
                'trades': 0,
                'profit_factor': 0,
            })

    return pd.DataFrame(results)


# ==================== 병렬 처리 함수 ====================

def _run_single_backtest(args: tuple) -> dict:
    """
    단일 백테스트 실행 (멀티프로세스 워커 함수)

    Args:
        args: (symbol, param_name, value, base_params, df_pattern_dict, df_entry_dict)

    Returns:
        결과 딕셔너리
    """
    symbol, param_name, value, base_params, df_pattern_dict, df_entry_dict = args

    try:
        # DataFrame 재구성
        df_pattern = pd.DataFrame(df_pattern_dict)
        df_entry = pd.DataFrame(df_entry_dict)

        # 파라미터 설정
        test_params = base_params.copy()
        test_params[param_name] = value

        # 백테스트 실행
        from utils.metrics import calculate_backtest_metrics

        strategy = AlphaX7Core()
        trades = strategy.run_backtest(df_pattern, df_entry, **test_params)

        # Type guard and conversion (same as single-threaded version)
        if isinstance(trades, list):
            metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)
        else:
            metrics = trades

        return {
            'param_value': value,
            'win_rate': metrics.get('win_rate', 0),
            'total_return': metrics.get('total_pnl', 0),  # ✅ Fixed: 'total_return' → 'total_pnl'
            'mdd': metrics.get('mdd', 0),  # ✅ Fixed: 'max_drawdown' → 'mdd'
            'sharpe': metrics.get('sharpe_ratio', 0),
            'trades': metrics.get('total_trades', 0),
            'profit_factor': metrics.get('profit_factor', 0),
            'success': True,
        }

    except Exception as e:
        return {
            'param_value': value,
            'win_rate': 0,
            'total_return': 0,
            'mdd': 100,
            'sharpe': 0,
            'trades': 0,
            'profit_factor': 0,
            'success': False,
            'error': str(e),
        }


def analyze_single_parameter_parallel(
    symbol: str,
    param_name: str,
    param_values: List,
    base_params: Dict,
    df_pattern: pd.DataFrame,
    df_entry: pd.DataFrame,
    mode: str = 'deep'
) -> pd.DataFrame:
    """
    단일 파라미터의 민감도 분석 (병렬 처리)

    Args:
        symbol: 심볼
        param_name: 파라미터 이름
        param_values: 테스트할 값 리스트
        base_params: 기본 파라미터 (고정값)
        df_pattern: 패턴 데이터
        df_entry: 엔트리 데이터
        mode: 최적화 모드 (워커 수 결정)

    Returns:
        결과 DataFrame
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"파라미터 분석 (병렬): {param_name}")
    logger.info(f"테스트 범위: {param_values}")

    # 워커 수 계산
    max_workers = get_optimal_workers(mode)
    info = get_worker_info(mode)
    logger.info(f"워커: {info['workers']}/{info['total_cores']} 코어 ({info['usage_percent']:.0f}% 사용)")
    logger.info(f"{'='*60}")

    # DataFrame을 dict로 변환 (직렬화 가능)
    df_pattern_dict = df_pattern.to_dict('list')
    df_entry_dict = df_entry.to_dict('list')

    # 작업 목록 생성
    tasks = [
        (symbol, param_name, value, base_params, df_pattern_dict, df_entry_dict)
        for value in param_values
    ]

    # 병렬 실행
    results = []
    completed = 0
    total = len(tasks)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_single_backtest, task): task[2] for task in tasks}

        for future in as_completed(futures):
            value = futures[future]
            result = future.result()
            results.append(result)

            completed += 1

            # 진행률 표시
            if result['success']:
                logger.info(
                    f"[{completed}/{total}] {param_name}={value:6} → "
                    f"승률 {result['win_rate']:5.1f}% | "
                    f"수익 {result['total_return']:7.2f}% | "
                    f"MDD {result['mdd']:5.2f}% | "
                    f"거래 {result['trades']:4}회"
                )
            else:
                logger.error(f"[{completed}/{total}] {param_name}={value} 실패: {result.get('error', 'Unknown')}")

    return pd.DataFrame(results)


def calculate_sensitivity_score(df_results: pd.DataFrame) -> Dict:
    """
    파라미터 민감도 점수 계산

    민감도 = (최대값 - 최소값) / 평균값
    높을수록 해당 파라미터가 결과에 큰 영향을 미침

    Returns:
        {
            'win_rate_sensitivity': float,
            'return_sensitivity': float,
            'overall_score': float,
            'recommendation': str  # 'high', 'medium', 'low'
        }
    """
    # 승률 민감도
    wr_range = df_results['win_rate'].max() - df_results['win_rate'].min()
    wr_mean = df_results['win_rate'].mean()
    wr_sensitivity = wr_range / wr_mean if wr_mean > 0 else 0

    # 수익률 민감도
    ret_range = df_results['total_return'].max() - df_results['total_return'].min()
    ret_mean = abs(df_results['total_return'].mean())
    ret_sensitivity = ret_range / ret_mean if ret_mean > 0 else 0

    # Sharpe 민감도
    sharpe_range = df_results['sharpe'].max() - df_results['sharpe'].min()
    sharpe_mean = abs(df_results['sharpe'].mean())
    sharpe_sensitivity = sharpe_range / sharpe_mean if sharpe_mean > 0 else 0

    # 종합 점수 (가중 평균)
    overall_score = (
        wr_sensitivity * 0.4 +
        ret_sensitivity * 0.4 +
        sharpe_sensitivity * 0.2
    )

    # 권장사항
    if overall_score > 0.5:
        recommendation = 'high'  # 퀵 모드에서도 다양하게 탐색
    elif overall_score > 0.2:
        recommendation = 'medium'  # 스탠다드 모드에서 탐색
    else:
        recommendation = 'low'  # 딥 모드에서만 탐색

    return {
        'win_rate_sensitivity': wr_sensitivity,
        'return_sensitivity': ret_sensitivity,
        'sharpe_sensitivity': sharpe_sensitivity,
        'overall_score': overall_score,
        'recommendation': recommendation,
        'best_value': df_results.loc[df_results['total_return'].idxmax(), 'param_value'],
        'value_range': (df_results['param_value'].min(), df_results['param_value'].max()),
    }


def suggest_mode_ranges(sensitivity_results: Dict[str, Dict]) -> Dict:
    """
    민감도 분석 결과를 바탕으로 퀵/스탠다드/딥 모드 범위 제안

    Args:
        sensitivity_results: {param_name: sensitivity_score_dict}

    Returns:
        {
            'quick': {param: [values]},
            'standard': {param: [values]},
            'deep': {param: [values]}
        }
    """
    quick_ranges = {}
    standard_ranges = {}
    deep_ranges = {}

    for param_name, scores in sensitivity_results.items():
        recommendation = scores['recommendation']
        best_value = scores['best_value']
        full_range = DEEP_SEARCH_RANGES[param_name]

        if recommendation == 'high':
            # 민감도 높음 → 퀵에서도 충분히 탐색
            quick_ranges[param_name] = select_key_values(full_range, best_value, count=3)
            standard_ranges[param_name] = select_key_values(full_range, best_value, count=5)
            deep_ranges[param_name] = full_range

        elif recommendation == 'medium':
            # 민감도 중간 → 퀵은 베스트만, 스탠다드부터 탐색
            quick_ranges[param_name] = [best_value]
            standard_ranges[param_name] = select_key_values(full_range, best_value, count=4)
            deep_ranges[param_name] = full_range

        else:  # 'low'
            # 민감도 낮음 → 퀵/스탠다드는 고정, 딥만 탐색
            quick_ranges[param_name] = [best_value]
            standard_ranges[param_name] = [best_value]
            deep_ranges[param_name] = full_range

    return {
        'quick': quick_ranges,
        'standard': standard_ranges,
        'deep': deep_ranges,
    }


def select_key_values(full_range: List, best_value, count: int = 3) -> List:
    """
    전체 범위에서 핵심 값만 선택

    베스트 값 중심으로 균등하게 분포된 값들을 선택
    """
    if len(full_range) <= count:
        return full_range

    # 베스트 값의 인덱스
    try:
        best_idx = full_range.index(best_value)
    except ValueError:
        best_idx = len(full_range) // 2

    # 베스트 값을 중심으로 선택
    step = max(1, len(full_range) // count)
    selected = []

    # 베스트 값 포함
    selected.append(full_range[best_idx])

    # 좌우로 확장
    left_idx = best_idx - step
    right_idx = best_idx + step

    while len(selected) < count:
        if left_idx >= 0:
            selected.insert(0, full_range[left_idx])
            left_idx -= step

        if len(selected) >= count:
            break

        if right_idx < len(full_range):
            selected.append(full_range[right_idx])
            right_idx += step

    return sorted(set(selected))[:count]


def main():
    """메인 분석 루틴"""

    # 설정
    SYMBOL = 'BTCUSDT'
    EXCHANGE = 'bybit'

    # 데이터 로드
    logger.info(f"데이터 로딩: {EXCHANGE} {SYMBOL}")
    dm = BotDataManager(EXCHANGE, SYMBOL)

    if not dm.load_historical():
        logger.error("데이터 로드 실패")
        return

    df = dm.df_entry_full
    df_pattern = dm.df_pattern_full
    df_entry = dm.df_entry_resampled

    if df is None or df_pattern is None or df_entry is None:
        logger.error("데이터가 비어 있습니다 (필수 데이터프레임 누락)")
        return

    logger.info(f"데이터 기간: {df.index[0]} ~ {df.index[-1]} ({len(df):,}개)")

    # 기본 파라미터 (고정값)
    base_params = {
        'trend_interval': '1h',
        'filter_tf': '4h',
        'entry_tf': '15m',
        'leverage': 1,
        'direction': 'Both',
        'max_mdd': 20.0,

        # 기본값 설정
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'adx_period': 14,
        'adx_threshold': 25,
        'ema_period': 20,
        'atr_mult': 2.0,
        'atr_period': 14,
        'rsi_period': 14,
        'pullback_rsi_long': 40,
        'pullback_rsi_short': 60,
        'trail_start_r': 1.0,
        'trail_dist_r': 0.35,
        'pattern_tolerance': 0.05,
        'entry_validity_hours': 24.0,
    }

    # 분석할 파라미터 (우선순위)
    priority_params = [
        'macd_fast',
        'macd_slow',
        'adx_period',
        'adx_threshold',
        'atr_mult',
        'rsi_period',
    ]

    # CPU 정보 출력
    info = get_worker_info('deep')
    logger.info(f"\n{'='*80}")
    logger.info(f"CPU 정보")
    logger.info(f"{'='*80}")
    logger.info(f"총 코어: {info['total_cores']}")
    logger.info(f"사용 워커: {info['workers']} ({info['usage_percent']:.0f}%)")
    logger.info(f"여유 코어: {info['free_cores']}")
    logger.info(f"설명: {info['description']}")
    logger.info(f"{'='*80}\n")

    # 민감도 분석
    all_results = {}
    sensitivity_scores = {}

    start_time = time.time()

    # 🔥 병렬 처리 사용
    USE_PARALLEL = True

    for param_name in priority_params:
        param_values = DEEP_SEARCH_RANGES[param_name]

        # 단일 파라미터 분석 (병렬 or 순차)
        if USE_PARALLEL:
            df_results = analyze_single_parameter_parallel(
                SYMBOL, param_name, param_values, base_params, df_pattern, df_entry, mode='deep'
            )
        else:
            df_results = analyze_single_parameter(
                SYMBOL, param_name, param_values, base_params, df_pattern, df_entry
            )

        # 민감도 계산
        scores = calculate_sensitivity_score(df_results)

        # 저장
        all_results[param_name] = df_results
        sensitivity_scores[param_name] = scores

        # 결과 출력
        logger.info(f"\n{'='*60}")
        logger.info(f"{param_name} 민감도 분석 결과:")
        logger.info(f"  승률 민감도: {scores['win_rate_sensitivity']:.3f}")
        logger.info(f"  수익 민감도: {scores['return_sensitivity']:.3f}")
        logger.info(f"  Sharpe 민감도: {scores['sharpe_sensitivity']:.3f}")
        logger.info(f"  종합 점수: {scores['overall_score']:.3f}")
        logger.info(f"  권장사항: {scores['recommendation'].upper()}")
        logger.info(f"  최적값: {scores['best_value']}")
        logger.info(f"{'='*60}\n")

    elapsed = time.time() - start_time
    logger.info(f"\n총 분석 시간: {elapsed/60:.1f}분")

    # 모드별 범위 제안
    logger.info("\n" + "="*80)
    logger.info("퀵/스탠다드/딥 모드 범위 제안")
    logger.info("="*80)

    mode_ranges = suggest_mode_ranges(sensitivity_scores)

    for mode, ranges in mode_ranges.items():
        logger.info(f"\n## {mode.upper()} 모드")
        logger.info("-" * 60)
        for param, values in ranges.items():
            logger.info(f"  '{param}': {values},")

    # CSV 저장
    output_dir = project_root / 'docs'
    output_dir.mkdir(exist_ok=True)

    for param_name, df_results in all_results.items():
        csv_path = output_dir / f'sensitivity_{param_name}.csv'
        df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"저장: {csv_path}")

    # 요약 리포트 저장
    report_path = output_dir / 'INDICATOR_SENSITIVITY_REPORT.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 지표 민감도 분석 리포트\n\n")
        f.write(f"분석 일시: {pd.Timestamp.now()}\n")
        f.write(f"분석 대상: {EXCHANGE} {SYMBOL}\n")
        f.write(f"분석 시간: {elapsed/60:.1f}분\n\n")

        f.write("## 민감도 요약\n\n")
        f.write("| 파라미터 | 종합 점수 | 권장사항 | 최적값 |\n")
        f.write("|---------|----------|---------|--------|\n")
        for param, scores in sensitivity_scores.items():
            f.write(f"| {param} | {scores['overall_score']:.3f} | "
                   f"{scores['recommendation'].upper()} | {scores['best_value']} |\n")

        f.write("\n## 모드별 권장 범위\n\n")
        for mode, ranges in mode_ranges.items():
            f.write(f"\n### {mode.upper()} 모드\n\n")
            f.write("```python\n")
            f.write(f"{mode.upper()}_RANGE = {{\n")
            for param, values in ranges.items():
                f.write(f"    '{param}': {values},\n")
            f.write("}\n```\n")

    logger.info(f"\n리포트 저장: {report_path}")

    logger.info("\n분석 완료!")


if __name__ == '__main__':
    main()
