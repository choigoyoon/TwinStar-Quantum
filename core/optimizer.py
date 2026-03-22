# optimizer.py
"""
STAR-U Bot 최적화 엔진
- 파라미터 그리드 서치
- 결과 정렬 및 랭킹
- 최적값 반환
"""
import logging
logger = logging.getLogger(__name__)


import itertools
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Any, cast
from dataclasses import dataclass
from pathlib import Path
import multiprocessing as mp

# 메트릭 계산 (SSOT)
from utils.metrics import (
    assign_grade_by_preset
    # calculate_backtest_metrics는 calculate_metrics() 내부에서 동적 import
)

def optimize_strategy(symbol: str, timeframe: str, exchange: str = 'bybit') -> Optional[dict]:
    """배치 최적화에서 사용하는 래퍼 함수 (BatchOptimizer 호환)"""
    # Circular import 방지를 위해 내부에서 임포트
    from core.strategy_core import AlphaX7Core
    from core.data_manager import BotDataManager
    
    dm = BotDataManager(exchange, symbol, {'entry_tf': timeframe})
    if dm.load_historical() and dm.df_entry_full is not None:
        opt = BacktestOptimizer(AlphaX7Core, dm.df_entry_full)
        grid = generate_fast_grid(timeframe)
        results = opt.run_optimization(dm.df_entry_full, grid)
        if results:
            best = results[0]
            return {
                'win_rate': best.win_rate,
                'profit_factor': best.profit_factor,
                'max_drawdown': best.max_drawdown,
                'total_trades': best.trades,
                'best_params': best.params
            }
    return None

import sys
import os

# Logging
from utils.logger import get_module_logger
logger = get_module_logger(__name__)

# TF_MAPPING, TF_RESAMPLE_MAP import
# 상수 및 유틸리티 임포트 (Phase 3 SSOT)
from config.constants.timeframes import TF_MAPPING, TF_RESAMPLE_MAP
from config.parameters import DEFAULT_PARAMS
from utils.data_utils import resample_data as shared_resample


# ==================== CPU 워커 자동 계산 ====================

def get_numpy_threads() -> int:
    """
    NumPy/Pandas 내부 스레드 수 감지 (v7.29)

    Returns:
        NumPy가 사용하는 스레드 수 (기본값: 1)
    """
    # MKL/OpenBLAS 환경 변수 확인
    mkl_threads = os.environ.get('MKL_NUM_THREADS', None)
    openblas_threads = os.environ.get('OPENBLAS_NUM_THREADS', None)
    omp_threads = os.environ.get('OMP_NUM_THREADS', None)

    if mkl_threads:
        return int(mkl_threads)
    elif openblas_threads:
        return int(openblas_threads)
    elif omp_threads:
        return int(omp_threads)
    else:
        # 기본값: 1 (단일 스레드 가정)
        return 1


def get_optimal_workers(mode: str = 'standard', available_memory_gb: float | None = None) -> int:
    """
    최적 워커 수 자동 계산 (v7.29 - 물리 코어 + NumPy 스레드 고려)

    [OK] v7.29 개선:
    - 물리 코어 우선 사용 (100% 효율)
    - 하이퍼스레딩 보조 사용 (35% 효율, Deep 모드만)
    - NumPy 멀티스레딩 고려 (n_workers × numpy_threads ≤ logical_cores)
    - 메모리 제약 우선 적용

    Args:
        mode: 'quick', 'standard', 'deep'
        available_memory_gb: 사용 가능한 메모리 (GB). None이면 자동 감지

    Returns:
        워커 수 (1 ~ cpu_count)
    """
    # 1. 코어 감지
    try:
        import psutil
        physical_cores = psutil.cpu_count(logical=False) or 4
        logical_cores = psutil.cpu_count(logical=True) or 4
        hyperthreading = logical_cores > physical_cores
    except ImportError:
        # psutil 없으면 mp.cpu_count() 사용 (논리 코어)
        logical_cores = mp.cpu_count() or 4
        physical_cores = logical_cores  # 하이퍼스레딩 없다고 가정
        hyperthreading = False

    # 2. NumPy 멀티스레딩 감지
    numpy_threads = get_numpy_threads()

    # 3. 모드별 기본 워커 수 (물리 코어 기반)
    if mode == 'quick':
        base_workers = max(1, physical_cores // 2)  # 50% 사용
    elif mode == 'standard':
        base_workers = max(2, physical_cores - 1)   # 물리 코어 - 1
    elif mode == 'deep':
        if hyperthreading:
            # 물리 코어 전체 + 논리 코어 35% 활용
            ht_bonus = max(1, (logical_cores - physical_cores) // 3)
            base_workers = physical_cores + ht_bonus
        else:
            base_workers = max(2, physical_cores - 1)
    else:
        base_workers = max(2, physical_cores // 2)

    # 4. NumPy 멀티스레딩 고려한 워커 조정
    if numpy_threads > 1:
        # 총 스레드 = n_workers × numpy_threads ≤ logical_cores
        max_workers_by_numpy = logical_cores // numpy_threads
        workers = min(base_workers, max_workers_by_numpy)
    else:
        workers = base_workers

    # 5. 메모리 제약 (v7.28 기존 로직)
    if available_memory_gb is None:
        try:
            import psutil
            available_memory_gb = psutil.virtual_memory().available / (1024 ** 3)
        except ImportError:
            available_memory_gb = 999.0

    # 메모리 제약 적용
    if available_memory_gb < 2.0:
        workers = min(workers, 2)
    elif available_memory_gb < 4.0:
        workers = min(workers, 4)
    elif available_memory_gb < 8.0:
        workers = min(workers, 6)

    return max(1, workers)


def get_worker_info(mode: str = 'standard') -> dict:
    """
    워커 정보 반환 (로깅/GUI 표시용, v7.29: 물리 코어 + NumPy 스레드 정보 추가)

    Returns:
        {
            'total_cores': int,              # 논리 코어 (하이퍼스레딩 포함)
            'physical_cores': int,           # v7.29 신규: 물리 코어
            'hyperthreading': bool,          # v7.29 신규: 하이퍼스레딩 여부
            'numpy_threads': int,            # v7.29 신규: NumPy 내부 스레드
            'workers': int,
            'total_threads': int,            # v7.29 신규: workers × numpy_threads
            'usage_percent': float,
            'description': str,
            'free_cores': int,
            'available_memory_gb': float,
            'memory_limited': bool
        }
    """
    # 1. 코어 정보 수집
    try:
        import psutil
        physical_cores = psutil.cpu_count(logical=False) or 4
        logical_cores = psutil.cpu_count(logical=True) or 4
        hyperthreading = logical_cores > physical_cores
        available_memory_gb = psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        logical_cores = mp.cpu_count() or 1
        physical_cores = logical_cores
        hyperthreading = False
        available_memory_gb = -1.0

    # 2. NumPy 스레드 정보
    numpy_threads = get_numpy_threads()

    # 3. 워커 계산
    workers = get_optimal_workers(mode, available_memory_gb)
    total_threads = workers * numpy_threads
    usage = (total_threads / logical_cores) * 100

    # 4. 메모리 제한 여부 판단
    cpu_only_workers = get_optimal_workers(mode, 999.0)  # 메모리 무제한
    memory_limited = (workers < cpu_only_workers)

    # 5. 설명 생성
    descriptions = {
        'quick': f'빠른 모드 (CPU {usage:.0f}% 사용)',
        'standard': f'표준 모드 (CPU {usage:.0f}% 사용)',
        'deep': f'딥 모드 (CPU {usage:.0f}% 사용, 최대 성능)',
    }
    desc = descriptions.get(mode, '알 수 없음')

    # 6. NumPy 멀티스레딩 정보 추가
    if numpy_threads > 1:
        desc += f' [NumPy: {numpy_threads}스레드]'

    # 7. 메모리 제한 시 설명 추가
    if memory_limited and available_memory_gb > 0:
        desc += f' [메모리 제약: {available_memory_gb:.1f}GB]'

    return {
        'total_cores': logical_cores,
        'physical_cores': physical_cores,        # v7.29
        'hyperthreading': hyperthreading,        # v7.29
        'numpy_threads': numpy_threads,          # v7.29
        'workers': workers,
        'total_threads': total_threads,          # v7.29
        'usage_percent': usage,
        'description': desc,
        'free_cores': logical_cores - total_threads,
        'available_memory_gb': available_memory_gb,
        'memory_limited': memory_limited
    }


# ==================== 최적화 상수 ====================

# 리샘플링 가능한 TF
AVAILABLE_TF = ['15m', '30m', '45m', '1h', '2h', '3h', '4h', '6h', '12h', '1d', '1w']

# 추세 TF별 자동 탐색 범위 (v2.0 - 필터 강화)
TF_AUTO_RANGE = {
    '1h': {
        'filter_tf': ['4h', '6h', '12h', '1d'],  # 2h 제거 (너무 약함)
        'entry_tf': ['15m', '30m', '45m']
    },
    '4h': {
        'filter_tf': ['1d', '1w'],  # 6h, 12h 제거 (필터 강화)
        'entry_tf': ['15m', '30m', '1h', '2h']
    },
    '1d': {
        'filter_tf': ['1w'],
        'entry_tf': ['1h', '2h', '4h', '6h', '12h']
    },
    '1w': {
        'filter_tf': ['1d'],
        'entry_tf': ['4h', '6h', '12h', '1d']
    }
}

# 배율 범위
LEVERAGE_RANGE = [1, 2, 3, 5, 7, 10, 15, 20]

# 방향 범위
DIRECTION_RANGE = ['Both', 'Long', 'Short']

# 지표 범위 설정 (Standard 모드 기본값, 하위 호환성)
INDICATOR_RANGE = {
    'macd_fast': [6, 8, 10, 12],
    'macd_slow': [18, 20, 24, 26, 32],
    'macd_signal': [7, 9, 12],
    'ema_period': [10, 20, 50],

    # 기존 유지 및 최적화
    'atr_mult': [1.0, 1.5, 2.0, 2.2],
    'atr_period': [7, 14, 21],
    'rsi_period': [7, 14, 21],
    'trail_start_r': [0.5, 0.7, 1.0],
    'trail_dist_r': [0.2, 0.35, 0.5],
    'pullback_rsi_long': [35, 40, 45],
    'pullback_rsi_short': [55, 60, 65],
    'pattern_tolerance': [0.03, 0.04, 0.05],
    'entry_validity_hours': [12, 24, 48],
    'max_adds': [0, 1, 2],
}

# ==================== 모드별 지표 범위 ====================

# Quick 모드 (최소 조합, 4개) - 승률 80%+ & 매매빈도 0.5회/일 목표
# [OK] DEFAULT_PARAMS 포함: atr_mult=1.25, rsi_period=14, entry_validity_hours=6
INDICATOR_RANGE_QUICK = {
    'macd_fast': [8, 12],
    'macd_slow': [20, 26],
    'macd_signal': [9],
    'ema_period': [20, 50],
    'atr_mult': [1.25, 2.5],             # 2개 - 최적값(1.25) + 보수값(2.5)
    'atr_period': [14],
    'rsi_period': [14],                  # 1개 - 표준값 (고정)
    'trail_start_r': [0.7, 1.0],
    'trail_dist_r': [0.35, 0.5],
    'pullback_rsi_long': [40],
    'pullback_rsi_short': [60],
    'pattern_tolerance': [0.05],
    'entry_validity_hours': [6, 48],     # 2개 - 최적값(6) + 저빈도(48)
    'max_adds': [0, 1],
}
# 핵심 조합: 2 (atr_mult) × 1 (rsi_period) × 2 (entry_validity_hours) = 4개

# Standard 모드 (균형, 36개) - 승률 75%+ & 매매빈도 1-2회/일 목표
# [OK] DEFAULT_PARAMS 포함: atr_mult=1.25, rsi_period=14, entry_validity_hours=6
INDICATOR_RANGE_STANDARD = {
    'macd_fast': [6, 8, 10, 12],
    'macd_slow': [18, 20, 24, 26],
    'macd_signal': [7, 9, 12],
    'ema_period': [10, 20, 30, 50],
    'atr_mult': [1.25, 1.5, 2.0, 2.5],       # 4개 - 최적값(1.25) 포함
    'atr_period': [7, 14, 21],
    'rsi_period': [7, 14, 21],               # 3개 - 단기/표준/장기 균형
    'trail_start_r': [0.5, 0.7, 1.0, 1.2],
    'trail_dist_r': [0.2, 0.35, 0.5, 0.7],
    'pullback_rsi_long': [35, 40, 45],
    'pullback_rsi_short': [55, 60, 65],
    'pattern_tolerance': [0.03, 0.04, 0.05],
    'entry_validity_hours': [6, 12, 24],     # 3개 - 최적값(6) 포함
    'max_adds': [0, 1, 2],
}
# 핵심 조합: 4 (atr_mult) × 3 (rsi_period) × 3 (entry_validity_hours) = 36개

# Deep 모드 (완전 탐색, 252개) - 다양한 스타일 탐색 (공격×3, 균형, 보수, 고승률, 저빈도)
# [OK] DEFAULT_PARAMS 포함: atr_mult=1.25, rsi_period=14, entry_validity_hours=6
INDICATOR_RANGE_DEEP = {
    'atr_mult': [1.0, 1.25, 1.5, 2.0, 2.5, 3.0],  # 6개 - 최적값(1.25) 포함, 3.5 제거
    'rsi_period': [5, 7, 11, 14, 21, 25, 30],     # 7개 - 전체 범위
    'entry_validity_hours': [6, 12, 24, 36, 48, 72],  # 6개 - 최적값(6) 포함
}
# 핵심 조합: 6 (atr_mult) × 7 (rsi_period) × 6 (entry_validity_hours) = 252개


def get_indicator_range(mode: str = 'standard') -> Dict:
    """
    모드에 따른 지표 범위 반환

    Args:
        mode: 'quick', 'standard', 'deep'

    Returns:
        지표 범위 딕셔너리
    """
    mode = mode.lower()

    if mode == 'quick':
        return INDICATOR_RANGE_QUICK.copy()
    elif mode == 'deep':
        return INDICATOR_RANGE_DEEP.copy()
    else:
        return INDICATOR_RANGE_STANDARD.copy()





# ==================== Grid 생성 함수 ====================

def generate_full_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """
    Standard 모드용 Grid (~60개) - 승률 & 매매빈도 최적화
    """
    from config.parameters import get_param_range_by_mode, DEFAULT_PARAMS

    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])

    # None 방어: get_param_range_by_mode() 반환값 None 체크 + 기본값 폴백
    filter_tf = get_param_range_by_mode('filter_tf', 'standard') or [DEFAULT_PARAMS.get('filter_tf', '4h')]
    atr_mult = get_param_range_by_mode('atr_mult', 'standard') or [DEFAULT_PARAMS.get('atr_mult', 1.5)]
    trail_start_r = get_param_range_by_mode('trail_start_r', 'standard') or [DEFAULT_PARAMS.get('trail_start_r', 0.8)]
    trail_dist_r = get_param_range_by_mode('trail_dist_r', 'standard') or [DEFAULT_PARAMS.get('trail_dist_r', 0.1)]
    entry_validity_hours = get_param_range_by_mode('entry_validity_hours', 'standard') or [DEFAULT_PARAMS.get('entry_validity_hours', 6.0)]

    return {
        'trend_interval': [trend_tf],
        'filter_tf': filter_tf,                                              # 3개 ['4h', '6h', '12h']
        'entry_tf': [tf_range['entry_tf'][0]],                               # 1개 (15m)
        'leverage': [1],                                                      # 1개 (고정)
        'direction': ['Both'],                                                # 1개 (고정)
        'max_mdd': [max_mdd],                                                 # 1개 (고정)
        'atr_mult': atr_mult,                                                 # 4개 [1.25, 1.5, 2.0, 2.5]
        'trail_start_r': trail_start_r,                                       # 4개 [1.0, 1.5, 2.0, 2.5]
        'trail_dist_r': trail_dist_r,                                         # 2개 [0.2, 0.3]
        'pattern_tolerance': [0.05],                                          # 1개 (고정)
        'entry_validity_hours': entry_validity_hours,                         # 5개 [6, 12, 24, 48, 72]
        'pullback_rsi_long': [40],                                            # 1개 (고정)
        'pullback_rsi_short': [60],                                           # 1개 (고정)
        # Total: 3×1×1×1×1×4×4×2×1×5×1×1 = 120개 [OK]
    }



def generate_quick_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """Quick 모드용 최소 Grid (~8개) - 승률 80% & 매매빈도 0.5회/일 목표"""
    from config.parameters import get_param_range_by_mode, DEFAULT_PARAMS

    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])

    # None 방어: get_param_range_by_mode() 반환값 None 체크 + 기본값 폴백
    filter_tf = get_param_range_by_mode('filter_tf', 'quick') or [DEFAULT_PARAMS.get('filter_tf', '4h')]
    atr_mult = get_param_range_by_mode('atr_mult', 'quick') or [DEFAULT_PARAMS.get('atr_mult', 1.5)]
    trail_start_r = get_param_range_by_mode('trail_start_r', 'quick') or [DEFAULT_PARAMS.get('trail_start_r', 0.8)]
    trail_dist_r = get_param_range_by_mode('trail_dist_r', 'quick') or [DEFAULT_PARAMS.get('trail_dist_r', 0.1)]
    entry_validity_hours = get_param_range_by_mode('entry_validity_hours', 'quick') or [DEFAULT_PARAMS.get('entry_validity_hours', 6.0)]

    return {
        'trend_interval': [trend_tf],
        'filter_tf': filter_tf,                                                # 2개 ['12h', '1d']
        'entry_tf': [tf_range['entry_tf'][0]],                                # 1개 (15m 고정)
        'leverage': [1],                                                       # 1개 (고정)
        'direction': ['Both'],                                                 # 1개 (고정)
        'max_mdd': [max_mdd],                                                  # 1개 (고정)
        'atr_mult': atr_mult,                                                  # 2개 [1.25, 2.0]
        'trail_start_r': trail_start_r,                                        # 2개 [1.0, 1.5]
        'trail_dist_r': trail_dist_r,                                          # 1개 [0.2]
        'pattern_tolerance': [0.05],                                           # 1개 (고정)
        'entry_validity_hours': entry_validity_hours,                          # 2개 [48, 72]
        'pullback_rsi_long': [40],                                             # 1개 (고정)
        'pullback_rsi_short': [60],                                            # 1개 (고정)
        # Total: 2×1×1×1×1×2×2×1×1×2×1×1 = 8개 [OK]
    }



def generate_standard_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """
    [DEPRECATED v7.21] Standard 모드 제거됨

    Standard 모드는 Quick/Deep으로 충분하며 Meta가 가장 효율적입니다.
    하위 호환성을 위해 Quick 그리드로 fallback합니다.

    Args:
        trend_tf: 타임프레임
        max_mdd: 최대 MDD

    Returns:
        Quick 모드 그리드 (하위 호환성)
    """
    import warnings
    warnings.warn(
        "generate_standard_grid()는 v7.21에서 deprecated되었습니다. "
        "Meta 모드를 사용하거나 Quick/Deep 모드를 선택하세요.",
        DeprecationWarning,
        stacklevel=2
    )
    return generate_quick_grid(trend_tf, max_mdd)

def generate_deep_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """Deep 모드용 정밀 Grid (~1,080개) - 전수 조사"""
    from config.parameters import get_param_range_by_mode, DEFAULT_PARAMS

    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])

    # None 방어: get_param_range_by_mode() 반환값 None 체크 + 기본값 폴백
    filter_tf = get_param_range_by_mode('filter_tf', 'deep') or [DEFAULT_PARAMS.get('filter_tf', '4h')]
    atr_mult = get_param_range_by_mode('atr_mult', 'deep') or [DEFAULT_PARAMS.get('atr_mult', 1.5)]
    trail_start_r = get_param_range_by_mode('trail_start_r', 'deep') or [DEFAULT_PARAMS.get('trail_start_r', 0.8)]
    trail_dist_r = get_param_range_by_mode('trail_dist_r', 'deep') or [DEFAULT_PARAMS.get('trail_dist_r', 0.1)]
    entry_validity_hours = get_param_range_by_mode('entry_validity_hours', 'deep') or [DEFAULT_PARAMS.get('entry_validity_hours', 6.0)]
    
    # 가변 엔진 파라미터 추가 (v7.41)
    range_low_slope = get_param_range_by_mode('range_low_slope', 'deep') or [0.012]
    range_high_slope = get_param_range_by_mode('range_high_slope', 'deep') or [0.035]
    precision_mult = get_param_range_by_mode('precision_mult', 'deep') or [0.7]
    aggressive_mult = get_param_range_by_mode('aggressive_mult', 'deep') or [1.5]
    precision_rsi_offset = get_param_range_by_mode('precision_rsi_offset', 'deep') or [7.0]
    aggressive_rsi_offset = get_param_range_by_mode('aggressive_rsi_offset', 'deep') or [10.0]

    return {
        'trend_interval': [trend_tf],
        'filter_tf': filter_tf,                                               # 5개 ['2h', '4h', '6h', '12h', '1d']
        'entry_tf': [tf_range['entry_tf'][0]],                               # 1개 (15m 고정)
        'leverage': [1],                                                      # 1개 (고정)
        'direction': ['Both'],                                                # 1개 (고정)
        'max_mdd': [max_mdd],                                                 # 1개 (고정)
        'atr_mult': atr_mult,                                                 # 6개
        'trail_start_r': [trail_start_r[i] for i in range(0, len(trail_start_r), 2)], # 6개 -> 3개 (샘플링)
        'trail_dist_r': [trail_dist_r[i] for i in range(0, len(trail_dist_r), 2)],   # 4개 -> 2개 (샘플링)
        'pattern_tolerance': [0.05],                                          # 1개
        'entry_validity_hours': [entry_validity_hours[0], entry_validity_hours[-1]], # 7개 -> 2개
        'pullback_rsi_long': [40],                                            # 1개
        'pullback_rsi_short': [60],                                           # 1개
        # 가변 엔진 (Adaptive) 파라미터 활성화
        'range_low_slope': [range_low_slope[1], range_low_slope[3]],         # 0.01, 0.02
        'range_high_slope': [range_high_slope[0], range_high_slope[3]],        # 0.025, 0.04
        'precision_mult': [precision_mult[1], precision_mult[4]],            # 0.6, 0.9
        'aggressive_mult': [aggressive_mult[1], aggressive_mult[3]],         # 1.4, 1.8
        'precision_rsi_offset': [precision_rsi_offset[1], precision_rsi_offset[3]], # 5.0, 12.0
        'aggressive_rsi_offset': [aggressive_rsi_offset[1], aggressive_rsi_offset[3]], # 10.0, 20.0
        # Total: 5(tf) * 6(atr) * 3(trail_s) * 2(trail_d) * 2(ev) * 2(slope_l) * 2(slope_h) * 2(p_m) * 2(a_m) * 2(p_o) * 2(a_o) = 23,040 조합 (v7.42)
    }


def generate_adaptive_grid(trend_tf: str, max_mdd: float = 20.0, sample_ratio: float = 0.33) -> Dict:
    """
    Adaptive 샘플링 Grid 생성 (v7.29 - 성능 최적화)

    전략:
    - 핵심 파라미터 (atr_mult, filter_tf): 100% 검사
    - 보조 파라미터 (trail_start_r, trail_dist_r, entry_validity_hours): 계층 샘플링
    - 목표: 1,080개 → 360개 (33% 검사, -67%)

    Args:
        trend_tf: 추세 타임프레임
        max_mdd: 최대 낙폭 허용치
        sample_ratio: 샘플링 비율 (기본값: 0.33 = 33%)

    Returns:
        Adaptive 샘플링된 파라미터 그리드

    Examples:
        # 기본 33% 샘플링
        grid = generate_adaptive_grid('1h')  # 360개 조합

        # 50% 샘플링 (더 정밀)
        grid = generate_adaptive_grid('1h', sample_ratio=0.5)  # 540개 조합
    """
    from config.parameters import get_param_range_by_mode, DEFAULT_PARAMS

    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])

    # 전체 범위 가져오기
    filter_tf_full = get_param_range_by_mode('filter_tf', 'deep') or [DEFAULT_PARAMS.get('filter_tf', '4h')]
    atr_mult_full = get_param_range_by_mode('atr_mult', 'deep') or [DEFAULT_PARAMS.get('atr_mult', 1.5)]
    trail_start_r_full = get_param_range_by_mode('trail_start_r', 'deep') or [DEFAULT_PARAMS.get('trail_start_r', 0.8)]
    trail_dist_r_full = get_param_range_by_mode('trail_dist_r', 'deep') or [DEFAULT_PARAMS.get('trail_dist_r', 0.1)]
    entry_validity_hours_full = get_param_range_by_mode('entry_validity_hours', 'deep') or [DEFAULT_PARAMS.get('entry_validity_hours', 6.0)]

    # [OK] 계층 샘플링 (중요도 기반)
    # Level 1: atr_mult (가장 중요, MDD 직접 영향) → 100% 검사
    atr_mult = atr_mult_full  # 6개 전체

    # Level 2: filter_tf (추세 필터) → 100% 검사
    filter_tf = filter_tf_full  # 5개 전체

    # Level 3: trail_start_r (수익 보호) → 50% 샘플링
    trail_start_r = [trail_start_r_full[i] for i in range(0, len(trail_start_r_full), 2)]  # 6개 → 3개

    # Level 4: trail_dist_r (익절 타이밍) → 50% 샘플링
    trail_dist_r = [trail_dist_r_full[i] for i in range(0, len(trail_dist_r_full), 2)]  # 4개 → 2개

    # Level 5: entry_validity_hours (매매 빈도) → 30% 샘플링
    entry_validity_hours = [entry_validity_hours_full[0], entry_validity_hours_full[-1]]  # 7개 → 2개 (양 끝)

    return {
        'trend_interval': [trend_tf],
        'filter_tf': filter_tf,                        # 5개 (100%)
        'entry_tf': [tf_range['entry_tf'][0]],        # 1개
        'leverage': [1],                               # 1개
        'direction': ['Both'],                         # 1개
        'max_mdd': [max_mdd],                         # 1개
        'atr_mult': atr_mult,                         # 6개 (100%)
        'trail_start_r': trail_start_r,               # 3개 (50%)
        'trail_dist_r': trail_dist_r,                 # 2개 (50%)
        'pattern_tolerance': [0.05],                  # 1개
        'entry_validity_hours': entry_validity_hours, # 2개 (30%)
        'pullback_rsi_long': [40],                    # 1개
        'pullback_rsi_short': [60],                   # 1개
        # Total: 5×1×1×1×1×6×3×2×1×2×1×1 = 360개 (-67%) [OK]
    }


def generate_grid_by_mode(
    trend_tf: str,
    mode: str = 'meta',  # v7.21: 기본값 'meta'로 변경
    max_mdd: float = 20.0,
    use_indicator_ranges: bool = False  # 기본값 False로 변경 (중복 방지)
) -> Dict:
    """
    모드에 따라 적절한 그리드 생성 (통합 함수)

    Args:
        trend_tf: 추세 타임프레임
        mode: 'meta', 'quick', 'deep' (v7.21: standard 제거)
        max_mdd: 최대 낙폭 허용치
        use_indicator_ranges: True면 모드별 지표 범위 사용, False면 기존 그리드 유지

    Returns:
        파라미터 그리드

    Examples:
        Meta 모드 (20초, ~3,000개) - 권장:
            grid = generate_grid_by_mode('1h', 'meta')

        Quick 모드 (2분, ~8개):
            grid = generate_grid_by_mode('1h', 'quick')

        Deep 모드 (2분, ~1,080개):
            grid = generate_grid_by_mode('1h', 'deep')
    """
    mode = mode.lower()

    # Standard 모드 deprecated 경고 (v7.21)
    if mode == 'standard':
        import warnings
        warnings.warn(
            "Standard 모드는 v7.21에서 제거되었습니다. Quick 모드로 fallback합니다.",
            DeprecationWarning,
            stacklevel=2
        )
        mode = 'quick'

    # 기존 그리드 함수 사용 (하위 호환성)
    if mode == 'quick':
        grid = generate_quick_grid(trend_tf, max_mdd)
    elif mode == 'deep':
        grid = generate_deep_grid(trend_tf, max_mdd)
    else:
        grid = generate_standard_grid(trend_tf, max_mdd)

    # 모드별 지표 범위 적용 (선택적)
    if use_indicator_ranges:
        indicator_range = get_indicator_range(mode)

        # 지표 범위 병합 (기존 grid 우선, 누락된 지표만 추가)
        for key, values in indicator_range.items():
            if key not in grid:
                grid[key] = values

    return grid


# ==================== 모드별 결과 개수 상수 ====================
MODE_RESULT_COUNT = {
    'quick': 1,      # 최적 1개
    'standard': 3,   # 공격, 균형, 보수
    'deep': 5,       # 공격×3, 균형, 보수 (+ 고승률, 저빈도 = 최대 7개)
}


def is_admin_mode() -> bool:
    """
    관리자 권한 체크 (Windows)
    Deep 모드 사용 시 관리자 권한 필요
    
    Returns:
        True if running as admin, False otherwise
    """
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        # Windows가 아닌 경우 또는 체크 실패 시 True 반환 (제한 없음)
        return True


def get_mode_from_grid(grid: Dict) -> str:
    """
    Grid 조합 수에 따라 자동으로 모드 결정
    
    Args:
        grid: 파라미터 그리드
    
    Returns:
        'quick', 'standard', or 'deep'
    """
    total, _ = estimate_combinations(grid)
    
    if total <= 200:
        return 'quick'
    elif total <= 10000:
        return 'standard'
    else:
        return 'deep'


def validate_deep_mode() -> tuple:
    """
    Deep 모드 사용 가능 여부 검증
    
    Returns:
        (can_use: bool, message: str)
    """
    if not is_admin_mode():
        return False, "[WARNING] Deep 모드는 관리자 권한이 필요합니다. 관리자로 실행해주세요."
    
    # 메모리 체크 (최소 8GB 권장)
    try:
        import psutil
        available_gb = psutil.virtual_memory().available / (1024**3)
        if available_gb < 4:
            return False, f"[WARNING] Deep 모드는 최소 4GB 메모리가 필요합니다. (현재: {available_gb:.1f}GB)"
    except ImportError:
        pass  # psutil 없으면 체크 스킵
    
    return True, "[OK] Deep 모드 사용 가능"



def generate_fast_grid(trend_tf: str, max_mdd: float = 20.0) -> Dict:
    """
    빠른 탐색용 축소 Grid 생성
    - INDICATOR_RANGE에서 성긴(Sparse) 형태로 샘플링
    
    Args:
        trend_tf: 추세 타임프레임
        max_mdd: 최대 허용 MDD (%)
    
    Returns:
        축소된 파라미터 grid dict
    """
    tf_range = TF_AUTO_RANGE.get(trend_tf, TF_AUTO_RANGE['1h'])
    
    # INDICATOR_RANGE에서 징검다리식으로 선택 (데이터 수 대폭 감소)
    grid = {
        'trend_interval': [trend_tf],
        'filter_tf': [tf_range['filter_tf'][0]],      # 최적 후보 1개
        'entry_tf': [tf_range['entry_tf'][0]],        # 최적 후보 1개
        'leverage': [3, 10],                          # 2단계 생략
        'direction': ['Both'],                         # 기본 방향
        'max_mdd': [max_mdd],
        'atr_mult': [1.25, 1.35, 1.5],                 # [MOD] 보수적 범위로 제한
        'trail_start_r': INDICATOR_RANGE['trail_start_r'][::3], # [0.5, 0.8, 1.1]
        'trail_dist_r': INDICATOR_RANGE['trail_dist_r'][::3],   # [0.1, 0.25, 0.4]
    }
    
    return grid


def estimate_combinations(grid: Dict) -> tuple:
    """
    파라미터 조합 수 및 예상 시간 계산
    
    Args:
        grid: 파라미터 grid dict
    
    Returns:
        (조합수, 예상시간분)
    """
    total = 1
    for key, values in grid.items():
        if isinstance(values, list):
            total *= len(values)
    
    # 백테스트 1회당 약 0.05초 가정
    estimated_seconds = total * 0.05
    estimated_minutes = estimated_seconds / 60
    
    return (total, round(estimated_minutes, 1))


@dataclass
class OptimizationResult:
    """
    최적화 결과 데이터
    
    ===============================================================
    [CHART] 지표별 영향 관계 (METRICS IMPACT REFERENCE)
    ===============================================================
    
    [입력 파라미터] → [영향 지표]
    ---------------------------------------------------------------
    atr_mult (ATR 배수)
      → max_drawdown: ATR↑ = 넓은 SL = MDD↑
      → win_rate: ATR↑ = 여유있는 SL = 승률↑ (조기 청산 방지)
      → trades: 영향 적음
    
    trail_start_r (트레일링 시작 R배수)
      → simple_return/compound_return: 시작↑ = 더 많이 수익 확보 후 트레일링
      → win_rate: 시작↑ = 익절 확률↑
      → max_drawdown: 간접 영향
    
    trail_dist_r (트레일링 거리 R배수)
      → max_drawdown: 거리↑ = 청산 늦음 = MDD↑
      → simple_return: 거리↑ = 수익 더 추구 = 수익↑ or 반납
    
    leverage (레버리지)
      → simple_return/compound_return: 레버리지↑ = 수익률↑ (비례)
      → max_drawdown: 레버리지↑ = MDD↑ (비례)
      → sharpe_ratio: 변동성↑ = 샤프↓
    
    direction (방향: Long/Short/Both)
      → trades: Both = 거래↑↑
      → win_rate: 시장 상황에 따라 변동
    
    filter_tf (필터 타임프레임)
      → win_rate: 상위TF 필터 = 신호 품질↑ = 승률↑
      → trades: 엄격한 필터 = 거래↓
    
    entry_tf (진입 타임프레임)
      → trades: 작은TF = 기회↑ = 거래↑
      → win_rate: 타이밍 정확도에 영향
    ---------------------------------------------------------------
    
    [지표 계산 위치]
    win_rate: _calculate_metrics() → (수익거래/전체거래) × 100
    max_drawdown: _calculate_metrics() → 최고점 대비 최대 하락폭
    sharpe_ratio: _calculate_metrics() → (평균수익/표준편차) × √252
    simple_return: _calculate_metrics() → Σ(각 거래 수익률)
    compound_return: _calculate_metrics() → Π(1+수익률) - 1
    ===============================================================
    """
    params: Dict                          # 사용된 파라미터
    trades: int                           # 매매 횟수 → direction, filter_tf, entry_tf 영향
    win_rate: float                       # 승률(%) → atr_mult, filter_tf 영향
    total_return: float                   # [DEPRECATED] simple_return 또는 compound_return 사용
    simple_return: float = 0.0            # 단리 수익률 → leverage, trail_* 영향
    compound_return: float = 0.0          # 복리 수익률 → leverage, trail_* 영향
    max_drawdown: float = 0.0             # MDD(%) → atr_mult, leverage, trail_dist_r 영향
    sharpe_ratio: float = 0.0             # 샤프비율 → leverage 영향 (변동성)
    profit_factor: float = 0.0            # 수익팩터 → 전체적 파라미터 영향
    avg_trades_per_day: float = 0.0       # 일평균 거래수
    stability: str = "[WARNING]" # 3구간 안정성 지표
    strategy_type: str = "" # 전략 유형 ([FIRE]공격, 균형, 보수)
    grade: str = ""                       # 등급 (S/A/B/C)
    capital_mode: str = "compound"        # 자본 모드
    avg_pnl: float = 0.0                  # [NEW] 평균 PnL (%)
    cagr: float = 0.0                     # [NEW] 연간 복리 수익률 (%)
    passes_filter: bool = True            # [NEW] 필터 통과 여부 (MDD, 승률, 거래수)
    symbol: str = ""                      # [NEW] 심볼 (백테스트용)
    timeframe: str = ""                   # [NEW] 타임프레임 (백테스트용)
    final_capital: float = 0.0            # [NEW] 최종 자본 (백테스트용)
    backtest_start_time: Optional[pd.Timestamp] = None  # [NEW] 백테스트 시작 시간 (v7.22)
    backtest_end_time: Optional[pd.Timestamp] = None    # [NEW] 백테스트 종료 시간 (v7.22)
    backtest_duration_days: int = 0       # [NEW] 백테스트 기간 (일) (v7.22)
    entry_validation_stats: Optional[Dict] = None  # [v7.30] Entry Validator 통계
    metrics_after_validation: Optional[Dict] = None  # [v7.30] Entry Validator 적용 후 메트릭


# calculate_grade() 함수 제거 (utils.metrics.assign_grade_by_preset()로 대체)
# 이전 위치: 라인 376-393
# 새로운 등급 시스템은 프리셋별 목표 기준을 사용합니다.


def extract_timestamps_from_trades(trades: List[Dict]) -> tuple[Optional[pd.Timestamp], Optional[pd.Timestamp], int]:
    """거래 리스트에서 타임스탬프 추출

    Args:
        trades: 백테스트 거래 리스트

    Returns:
        (start_time, end_time, duration_days)
        - start_time: 첫 거래 진입 시간
        - end_time: 마지막 거래 청산 시간
        - duration_days: 백테스트 기간 (일)

    Example:
        >>> trades = [{'entry_time': '2024-01-01', 'exit_time': '2024-01-02'}, ...]
        >>> start, end, days = extract_timestamps_from_trades(trades)
        >>> print(f"Period: {start} ~ {end} ({days} days)")
    """
    if not trades or len(trades) == 0:
        return None, None, 0

    try:
        # 첫 거래 진입 시간
        start_time = pd.to_datetime(trades[0]['entry_time'])

        # 마지막 거래 청산 시간
        end_time = pd.to_datetime(trades[-1]['exit_time'])

        # 기간 계산 (일)
        duration = (end_time - start_time).days

        return start_time, end_time, duration

    except (KeyError, ValueError, TypeError) as e:
        logger.debug(f"Failed to extract timestamps: {e}")
        return None, None, 0


def _worker_run_single(strategy_class, params, df_pattern, df_entry, slippage, fee):
    """멀티프로세싱 지원을 위한 독립형 워커 함수"""
    try:
        # 방향 처리
        leverage = params.get('leverage', 3)
        if isinstance(leverage, list): leverage = leverage[0]
        leverage = int(leverage)
        
        direction = params.get('direction', 'Both')
        if isinstance(direction, list): direction = direction[0]
        
        filter_tf = params.get('filter_tf', '4h')
        if isinstance(filter_tf, list): filter_tf = filter_tf[0]
        
        # 전략 인스턴스 생성
        # AlphaX7Core는 use_mtf=True, strategy_type 파라미터 필요
        use_mtf = params.get('use_mtf', True)  # 기본값 True
        strategy_type = params.get('strategy_type', 'macd')  # 기본값 'macd'
        try:
            strategy = strategy_class(use_mtf=use_mtf, strategy_type=strategy_type)
        except TypeError:
            # use_mtf/strategy_type 파라미터가 없는 전략 클래스
            try:
                strategy = strategy_class(use_mtf=use_mtf)
            except TypeError:
                strategy = strategy_class()
        
        # 총 비용
        total_cost = slippage + fee
        
        # 백테스트 실행 (v7.30 SSOT: DEFAULT_PARAMS에서 모든 기본값 참조)
        trades = strategy.run_backtest(
            df_pattern=df_pattern,
            df_entry=df_entry,
            slippage=total_cost,
            atr_mult=params.get('atr_mult', DEFAULT_PARAMS['atr_mult']),
            trail_start_r=params.get('trail_start_r', DEFAULT_PARAMS['trail_start_r']),
            trail_dist_r=params.get('trail_dist_r', DEFAULT_PARAMS['trail_dist_r']),
            pattern_tolerance=params.get('pattern_tolerance', DEFAULT_PARAMS['pattern_tolerance']),
            entry_validity_hours=params.get('entry_validity_hours', DEFAULT_PARAMS['entry_validity_hours']),
            pullback_rsi_long=params.get('pullback_rsi_long', DEFAULT_PARAMS['pullback_rsi_long']),
            pullback_rsi_short=params.get('pullback_rsi_short', DEFAULT_PARAMS['pullback_rsi_short']),
            max_adds=params.get('max_adds', DEFAULT_PARAMS['max_adds']),
            filter_tf=filter_tf,
            rsi_period=params.get('rsi_period', DEFAULT_PARAMS['rsi_period']),
            atr_period=params.get('atr_period', DEFAULT_PARAMS['atr_period']),
            macd_fast=params.get('macd_fast', DEFAULT_PARAMS['macd_fast']),
            macd_slow=params.get('macd_slow', DEFAULT_PARAMS['macd_slow']),
            macd_signal=params.get('macd_signal', DEFAULT_PARAMS['macd_signal']),
            ema_period=params.get('ema_period', DEFAULT_PARAMS['ema_period']),
            enable_pullback=params.get('enable_pullback', DEFAULT_PARAMS['enable_pullback']),
            # [v7.41] Adaptive Parameters 연동
            range_low_slope=params.get('range_low_slope', DEFAULT_PARAMS.get('range_low_slope', 0.012)),
            range_high_slope=params.get('range_high_slope', DEFAULT_PARAMS.get('range_high_slope', 0.035)),
            precision_mult=params.get('precision_mult', DEFAULT_PARAMS.get('precision_mult', 0.7)),
            aggressive_mult=params.get('aggressive_mult', DEFAULT_PARAMS.get('aggressive_mult', 1.5)),
            precision_rsi_offset=params.get('precision_rsi_offset', DEFAULT_PARAMS.get('precision_rsi_offset', 7.0)),
            aggressive_rsi_offset=params.get('aggressive_rsi_offset', DEFAULT_PARAMS.get('aggressive_rsi_offset', 10.0))
        )

        
        if not trades:
            return None
            
        min_trades = params.get('min_trades', 1)
        if len(trades) < min_trades:
            return None
            
        # 방향 필터링
        if direction != 'Both':
            trades = [t for t in trades if t['type'] == direction]
            if len(trades) < min_trades: return None
            
        # 레버리지 적용
        for t in trades:
            t['pnl'] = t['pnl'] * leverage
            
        # 메트릭 계산 (공용 정적 메서드 호출)
        metrics = BacktestOptimizer.calculate_metrics(trades)

        # MDD 필터
        max_mdd_limit = params.get('max_mdd', 100.0)
        if max_mdd_limit < 100.0 and abs(metrics['max_drawdown']) > max_mdd_limit:
            return None

        # 등급 할당 (strategy_type은 나중에 _classify_results()에서 할당)
        # 여기서는 균형형 기준으로 임시 등급 부여
        grade = assign_grade_by_preset(
            preset_type='balanced',
            metrics={
                'win_rate': metrics['win_rate'],
                'profit_factor': metrics['profit_factor'],
                'mdd': metrics['max_drawdown'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'compound_return': metrics['compound_return']
            }
        )

        # [NEW] 타임스탬프 추출 (v7.22)
        start_time, end_time, duration_days = extract_timestamps_from_trades(trades)

        return OptimizationResult(
            params=params,
            trades=len(trades),
            win_rate=metrics['win_rate'],
            total_return=metrics['total_return'],
            simple_return=metrics['simple_return'],
            compound_return=metrics['compound_return'],
            max_drawdown=metrics['max_drawdown'],
            sharpe_ratio=metrics['sharpe_ratio'],
            profit_factor=metrics['profit_factor'],
            avg_trades_per_day=metrics.get('avg_trades_per_day', 0.0),
            stability=metrics.get('stability', "[WARNING]"),
            grade=grade,
            avg_pnl=metrics.get('avg_pnl', 0.0),
            cagr=metrics.get('cagr', 0.0),
            backtest_start_time=start_time,      # [NEW] v7.22
            backtest_end_time=end_time,          # [NEW] v7.22
            backtest_duration_days=duration_days  # [NEW] v7.22
        )
    except Exception as e:
        # 디버깅: 예외 로깅
        import traceback
        logger.debug(f"Worker failed: {e}")
        logger.debug(traceback.format_exc())
        return None



    # _calculate_metrics_standalone removed and unified inside BacktestOptimizer



class BacktestOptimizer:
    """파라미터 그리드 서치 최적화"""
    
    # TF 매핑은 상단에서 import한 TF_MAPPING 사용
    
    def __init__(
        self,
        strategy_class,
        df: Optional[pd.DataFrame] = None,
        strategy_type: str = 'macd',
        exchange: str = 'bybit'
    ):
        """
        Args:
            strategy_class: X7PlusStrategy 등 전략 클래스
            df: 백테스트용 데이터프레임
            strategy_type: 전략 유형 ('macd' or 'adx')
            exchange: 거래소명 (v7.23 추가, 수수료 기반 범위 자동 조정)
        """
        self.strategy_class = strategy_class
        self.df = df
        self.strategy_type = strategy_type
        self.exchange = exchange  # v7.23: 거래소별 최적화
        self.results: List[OptimizationResult] = []
        self.progress_callback: Optional[Callable] = None
        self.cancelled = False
    
    def set_data(self, df: pd.DataFrame) -> None:
        """데이터 설정"""
        self.df = df
    
    def set_progress_callback(self, callback: Optional[Callable]) -> None:
        """진행률 콜백 설정"""
        self.progress_callback = callback
    
    def cancel(self) -> None:
        """최적화 취소"""
        self.cancelled = True
        
    def _resample(self, df: pd.DataFrame, target_tf: str, quiet: bool = False) -> pd.DataFrame:
        """15m → Target TF 리샘플링 (공용 함수 사용)"""
        # [FIX v7.26] 동일 타임프레임이면 리샘플링 건너뛰기
        # DataFrame이 이미 target_tf인지 확인 (캔들 수로 추정)
        if len(df) <= 55000:  # 1h 이상 타임프레임 (15m이면 203,823개)
            if not quiet:
                logger.info(f"[OPT] 리샘플링 건너뛰기: 이미 {target_tf} 데이터 ({len(df)}개)")
            # 지표만 추가
            if 'rsi' not in df.columns:
                from utils.indicators import add_all_indicators
                df = add_all_indicators(df.copy())
            return df

        # 공용 utils.data_utils.resample_data 사용
        if shared_resample:
            return shared_resample(df, target_tf, add_indicators=True)
        
        # Fallback: 로컬 구현
        rule = TF_RESAMPLE_MAP.get(target_tf, target_tf)
        df = df.copy()
        if 'datetime' not in df.columns:
            if pd.api.types.is_numeric_dtype(df['timestamp']):
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            else:
                df['datetime'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('datetime')
        resampled = df.resample(rule).agg({
            'timestamp': 'first', 'open': 'first', 'high': 'max',
            'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
        try:
            from utils.indicators import IndicatorGenerator
            resampled = IndicatorGenerator.add_all_indicators(resampled)
            if 'rsi' not in resampled.columns and 'rsi_14' in resampled.columns:
                resampled['rsi'] = resampled['rsi_14']
            if 'atr' not in resampled.columns and 'atr_14' in resampled.columns:
                resampled['atr'] = resampled['atr_14']
        except Exception as e:
            if not quiet: logger.info(f"[WARNING] 지표 재계산 실패: {e}")
        if not quiet: logger.info(f"[CHART] [OPT] 지표 재계산: {target_tf} ({len(resampled)}캔들)")
        return resampled
    
    def run_optimization(self, df: Optional[pd.DataFrame], grid: Dict, max_workers: int = 4,
                         metric: str = 'WinRate', task_callback: Optional[Callable] = None,
                         capital_mode: str = 'compound', n_cores: Optional[int] = None,
                         mode: str = 'standard', skip_filter: bool = False,
                         progress_callback: Optional[Callable[[int, int], None]] = None) -> List[OptimizationResult]:
        """
        그리드 서치 최적화 실행
        
        Args:
            df: 백테스트용 데이터프레임
            grid: 파라미터 그리드
            max_workers: 최대 워커 수 (deprecated, n_cores 사용)
            metric: 정렬 기준 메트릭
            task_callback: 작업 콜백
            capital_mode: 자본 모드 ('simple' or 'compound')
            n_cores: CPU 코어 수
            mode: 최적화 모드 ('quick'=1개, 'standard'=3개, 'deep'=5개+)
        
        Returns:
            최적화 결과 리스트
        """
        self.df = df
        self.results = []
        self.cancelled = False
        self.capital_mode = capital_mode.lower()
        if self.df is None or self.df.empty:
            raise ValueError("데이터가 설정되지 않았습니다")
        
        # [OK] v7.28: 저사양 PC 최적화 - 불필요한 복사 제거
        # df 복사 대신 inplace 변환 (메모리 절약)
        if not pd.api.types.is_datetime64_any_dtype(self.df['timestamp']):
            first_ts = self.df['timestamp'].iloc[0]
            if isinstance(first_ts, (int, float, np.number)) and first_ts > 100000000000:
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='ms', utc=True)
            else:
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        df = self.df  # 참조만 유지 (복사 안 함)

        self.cancelled = False
        self.results = []
        
        # 리샘플링 캐시 초기화
        self._resample_cache = {}
        
        # 모든 파라미터 조합 생성
        keys = list(grid.keys())
        values = list(grid.values())
        combinations = list(itertools.product(*values))
        total = len(combinations)
        
        # [NEW] n_cores 처리 (v7.29: 시스템 최적 워커 수 감지)
        if n_cores is None:
            n_cores = get_optimal_workers(mode)
        
        # [NEW] 지표 선행 계산 (ThreadPool 경합 방지)
        all_trend_tfs = set(grid.get('trend_interval', []))
        all_entry_tfs = set(grid.get('entry_tf', []))
        
        for tf in all_trend_tfs:
            key = f"p_{tf}"
            if key not in self._resample_cache:
                self._resample_cache[key] = self._resample(df, tf)
                
        for tf in all_entry_tfs:
            key = f"e_{tf}"
            if key not in self._resample_cache:
                if tf and tf not in ['15min', '15m']:
                    self._resample_cache[key] = self._resample(df, tf)
                else:
                    self._resample_cache[key] = df.copy()
        
        logger.info(f"Optimization started: {total} combinations, {n_cores} cores (Throttled ProcessPool)")
        
        # 병렬 처리 (ProcessPoolExecutor + Throttling)
        from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
        
        with ProcessPoolExecutor(max_workers=n_cores) as executor:
            # Throttled submission to avoid pickling overhead on Windows
            # 한꺼번에 수천 개를 제출하면 직렬화 부하로 30%대에서 멈추는 증상이 발생함
            max_queue = n_cores * 2
            futures_dict = {}
            combo_iter = iter(combinations)
            
            def submit_next():
                try:
                    combo = next(combo_iter)
                    params = dict(zip(keys, combo))
                    params['strategy_type'] = self.strategy_type
                    
                    trend_tf = params.get('trend_interval', '4h')
                    if isinstance(trend_tf, list): trend_tf = trend_tf[0]
                    entry_tf = params.get('entry_tf')
                    if isinstance(entry_tf, list): entry_tf = entry_tf[0]
                    if not entry_tf:
                        entry_tf = DEFAULT_PARAMS.get('entry_tf', '15m')
                    
                    df_pattern = self._resample_cache.get(f"p_{trend_tf}")
                    df_entry = self._resample_cache.get(f"e_{entry_tf}")

                    # 캐시 miss 방어
                    if df_pattern is None: df_pattern = self._resample(df, trend_tf, quiet=True)
                    if df_entry is None: df_entry = self._resample(df, entry_tf, quiet=True) if entry_tf not in ['15min', '15m'] else df.copy()

                    _leverage = params.get('leverage', 3)
                    if isinstance(_leverage, list): _leverage = _leverage[0]
                    _slippage = params.get('slippage', DEFAULT_PARAMS['slippage'])
                    _fee = params.get('fee', DEFAULT_PARAMS['fee'])

                    future = executor.submit(
                        _worker_run_single,
                        self.strategy_class,
                        params,
                        df_pattern,
                        df_entry,
                        _slippage,
                        _fee
                    )
                    futures_dict[future] = params
                    return True
                except StopIteration:
                    return False

            # 초기 큐 채우기
            for _ in range(min(total, max_queue)):
                submit_next()

            completed = 0
            while futures_dict:
                if self.cancelled:
                    logger.info("[NO] 최적화 취소됨")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                # 완료된 작업 대기
                done, _ = wait(futures_dict.keys(), return_when=FIRST_COMPLETED)
                
                for future in done:
                    params = futures_dict.pop(future)
                    completed += 1

                    # 진행률 콜백 호출 (파라미터 우선)
                    if progress_callback:
                        progress_callback(completed, total)
                    elif self.progress_callback:
                        self.progress_callback(int(completed / total * 100))

                    try:
                        result = future.result(timeout=60)
                        if result:
                            from config.parameters import OPTIMIZATION_FILTER
                            avg_trades_per_day = result.avg_trades_per_day

                            if skip_filter:
                                self.results.append(result)
                                if task_callback: task_callback(result)
                            else:
                                passes_filter = (
                                    result.win_rate >= OPTIMIZATION_FILTER['min_win_rate'] and
                                    abs(result.max_drawdown) <= OPTIMIZATION_FILTER['max_mdd'] and
                                    result.simple_return >= OPTIMIZATION_FILTER['min_total_return'] and
                                    avg_trades_per_day >= OPTIMIZATION_FILTER['min_trades_per_day'] and
                                    result.trades >= OPTIMIZATION_FILTER['min_absolute_trades']
                                )
                                if passes_filter:
                                    self.results.append(result)
                                    if task_callback: task_callback(result)
                    except Exception as e:
                        logger.debug(f"Task failed: {e}")

                    # 다음 작업 제출 ( replenishment )
                    submit_next()
        
        # 결과 정렬 및 상세 분류 (v2)
        if self.results:
            # 1. 지정된 메트릭으로 전체 정렬
            self.results.sort(key=lambda x: getattr(x, metric, 0), reverse=True)

            # 2. [NEW] v7.22: Coarse 모드는 분류 건너뛰기 (모든 결과 반환)
            if mode == 'coarse':
                logger.info(f"[WARNING] [Coarse Mode] Skipping classification, returning all results")
                # 상위 500개로 제한 (메모리 관리)
                self.results = self.results[:500]
            else:
                # 2. [NEW] 대표 유형 매칭 (원본 리스트는 유지하고 태깅만 수행)
                # 상위 1000개 결과 중 중복 없는 대표 유형들 선정
                top_results = self.results[:1000]
                unique_for_classification = self.filter_unique_results(top_results, max_count=100)
                representatives = self._classify_results(unique_for_classification, mode=mode)

                # 대표 유형들을 self.results 상단에 배치하고 나머지는 순서 유지
                rep_keys = [str(r.params) for r in representatives]
                final_list = representatives + [r for r in self.results if str(r.params) not in rep_keys]

                self.results = final_list[:2000] # 메모리 관리를 위해 상위 2000개로 제한


        # 리샘플링 캐시 정리 (메모리 해제)
        self._resample_cache = {}

        # ===================================
        # [v7.30] Entry Validator 자동 호출
        # ===================================
        if self.results and len(self.results) > 0:
            try:
                from core.entry_validator import filter_trades_with_entry_validation
                from utils.metrics import calculate_backtest_metrics

                # 최적 결과 (1등)
                best_result = self.results[0]

                # 최적 파라미터로 재백테스트 (거래 리스트 필요)
                logger.info("[VALIDATOR] O=H/O=L 제외 효과 분석 중...")

                # df_pattern, df_entry 준비
                trend_tf = best_result.params.get('trend_interval', '4h')
                if isinstance(trend_tf, list):
                    trend_tf = trend_tf[0]
                entry_tf = best_result.params.get('entry_tf', '1h')
                if isinstance(entry_tf, list):
                    entry_tf = entry_tf[0]

                df_pattern = self._resample(df, trend_tf, quiet=True) if df is not None else None
                df_entry = self._resample(df, entry_tf, quiet=True) if df is not None and entry_tf not in ['15min', '15m'] else df

                if df_pattern is not None and df_entry is not None:
                    # 백테스트 재실행
                    strategy_instance = self.strategy_class(use_mtf=True, strategy_type=self.strategy_type)
                    best_trades = strategy_instance.run_backtest(
                        df_pattern=df_pattern,
                        df_entry=df_entry,
                        **best_result.params
                    )

                    if best_trades and len(best_trades) > 0:
                        # Entry Validator 적용
                        filtered_trades, stats = filter_trades_with_entry_validation(
                            df_entry, best_trades, improvement_pct=0.00001
                        )

                        # Before vs After 메트릭
                        metrics_before = calculate_backtest_metrics(best_trades, leverage=1, capital=100)
                        metrics_after = calculate_backtest_metrics(filtered_trades, leverage=1, capital=100) if len(filtered_trades) > 0 else None

                        # 결과 출력
                        logger.info("=" * 60)
                        logger.info("O=H/O=L 제외 효과 분석")
                        logger.info("=" * 60)
                        logger.info(f"매매 횟수: {len(best_trades)} → {len(filtered_trades)} (-{stats['decline_rate']:.1f}%)")
                        logger.info(f"  - 지정가 미체결: {stats['limit_not_filled']}회")
                        logger.info(f"  - O=H 제외 (롱): {stats['oh_excluded']}회")
                        logger.info(f"  - O=L 제외 (숏): {stats['ol_excluded']}회")

                        if metrics_after:
                            win_rate_change = metrics_after['win_rate'] - metrics_before['win_rate']
                            sharpe_change = metrics_after['sharpe_ratio'] - metrics_before['sharpe_ratio']
                            logger.info(f"승률: {metrics_before['win_rate']:.2f}% → {metrics_after['win_rate']:.2f}% ({win_rate_change:+.2f}%p)")
                            logger.info(f"Sharpe: {metrics_before['sharpe_ratio']:.2f} → {metrics_after['sharpe_ratio']:.2f} ({sharpe_change:+.2f})")
                            logger.info(f"MDD: {metrics_before['mdd']:.2f}% → {metrics_after['mdd']:.2f}%")

                            # 권장 사항
                            if stats['decline_rate'] < 10 and win_rate_change > 0:
                                logger.info("[OK] 권장: O=H/O=L 제외 로직 적용 (성능 개선)")
                            elif stats['decline_rate'] >= 20:
                                logger.info("[WARNING] 매매 횟수 감소율 높음 (검토 필요)")
                        logger.info("=" * 60)

                        # 결과에 추가 정보 저장
                        best_result.entry_validation_stats = stats
                        if metrics_after:
                            best_result.metrics_after_validation = metrics_after

            except Exception as e:
                logger.warning(f"[WARNING] Entry Validator 실행 실패: {e}")
                # 에러가 발생해도 기존 결과는 반환

        logger.info(f"[OK] 최적화 완료: {len(self.results)}개 결과 반환")
        return self.results

    def save_results_to_csv(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        mode: str = 'deep',
        output_dir: str = 'data/optimization_results'
    ) -> str:
        """
        최적화 결과를 CSV로 저장

        Args:
            exchange: 거래소
            symbol: 심볼
            timeframe: 타임프레임
            mode: 최적화 모드
            output_dir: 출력 디렉토리

        Returns:
            저장된 CSV 파일 경로
        """
        from datetime import datetime

        if not self.results:
            raise ValueError("저장할 결과가 없습니다")

        # 1. DataFrame 생성
        rows = []
        for rank, result in enumerate(self.results, 1):
            row = {
                'rank': rank,
                'score': result.profit_factor * (result.win_rate / 100) if result.win_rate else 0,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor,
                'mdd': result.max_drawdown,
                'sharpe': result.sharpe_ratio,
                'sortino': getattr(result, 'sortino_ratio', 0),
                'calmar': getattr(result, 'calmar_ratio', 0),
                'trades': result.trades,
                'total_return': result.simple_return,
                **result.params  # 모든 파라미터 컬럼으로 추가
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        # 2. 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{exchange}_{symbol}_{timeframe}_{mode}_{timestamp}.csv"

        # 3. 저장
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        csv_path = output_path / filename

        df.to_csv(csv_path, index=False, encoding='utf-8')

        logger.info(f"CSV 저장 완료: {csv_path} ({len(df)} rows)")
        return str(csv_path)
    
    def _run_single(self, params: Dict, slippage: float, fee: float) -> Optional[OptimizationResult]:
        """단일 파라미터 조합으로 백테스트 실행"""
        if self.df is None:
            return None
            
        assert self.df is not None, "self.df cannot be None here"
        
        try:
            # 파라미터 추출 (리스트일 경우 단일 값으로 변환)
            filter_tf = params.get('filter_tf', '4h')
            if isinstance(filter_tf, list): filter_tf = filter_tf[0]
            
            trend_tf = params.get('trend_interval', '1h')
            if isinstance(trend_tf, list): trend_tf = trend_tf[0]
            
            # Entry TF: params에 있으면 사용, 없으면 TF_MAPPING
            entry_tf = params.get('entry_tf')
            if isinstance(entry_tf, list): entry_tf = entry_tf[0]
            if not entry_tf:
                entry_tf = TF_MAPPING.get(trend_tf, '15min')
            
            # [NEW] 리샘플링 캐시 사용 (성능 대폭 향상)
            if not hasattr(self, '_resample_cache'): self._resample_cache = {}
            
            # df_pattern 캐시 키
            p_key = f"p_{trend_tf}"
            if p_key not in self._resample_cache:
                self._resample_cache[p_key] = self._resample(self.df, trend_tf)
            df_pattern = self._resample_cache[p_key]
            
            # df_entry 캐시 키
            e_key = f"e_{entry_tf}"
            if e_key not in self._resample_cache:
                if entry_tf and entry_tf not in ['15min', '15m']:
                    self._resample_cache[e_key] = self._resample(self.df, entry_tf)
                else:
                    self._resample_cache[e_key] = self.df.copy()
            df_entry = self._resample_cache[e_key]
            
            # 배율/방향 처리
            leverage = params.get('leverage', 3)
            if isinstance(leverage, list): leverage = leverage[0]
            leverage = int(leverage)
            
            direction = params.get('direction', 'Both')
            if isinstance(direction, list): direction = direction[0]
            
            # 전략 생성 시 파라미터 전달
            init_params = {}
            if 'trend_interval' in params:
               init_params['trend_interval'] = params['trend_interval']
            
            # 계산된 entry_interval도 전달 (전략 내부 리샘플링용)
            init_params['entry_interval'] = entry_tf
            
            # 전략 인스턴스 생성 (Core)
            # strategy_class는 AlphaX7Core라고 가정 (또는 호환)
            # AlphaX7Core는 init에 df를 받지 않음. stateless.
            try:
                strategy = self.strategy_class()
                # params에 'rsi_period'가 있으면 전달해야 함
            except Exception:
                # 레거시 호환 (혹시 다른 전략을 쓸 경우)
                strategy = self.strategy_class(df=df, **init_params)
                if hasattr(strategy, 'prepare_data'):
                    strategy.prepare_data()
            
            # [OK] 총 비용 계산 (슬리피지 + 수수료)
            # [v7.26] 진입 비용 (Limit/Maker)
            # 청산 비용은 strategy_core.py에서 BACKTEST_EXIT_COST로 자동 차감 (0.065%)
            # 따라서 여기서는 진입 비용만 전달 (기본: 0.0002 = 0.02%)
            entry_cost = slippage + fee

            # 기본 파라미터와 병합 (DEFAULT_PARAMS 참조)
            backtest_params = {
                'slippage': entry_cost,  # DEPRECATED: 명칭 혼동, 실제로는 진입 비용
                'atr_mult': params.get('atr_mult', DEFAULT_PARAMS.get('atr_mult', 1.5)),
                'trail_start_r': params.get('trail_start_r', DEFAULT_PARAMS.get('trail_start_r', 0.8)),
                'trail_dist_r': params.get('trail_dist_r', DEFAULT_PARAMS.get('trail_dist_r', 0.5)),
                'pattern_tolerance': params.get('pattern_tolerance', DEFAULT_PARAMS.get('pattern_tolerance', 0.03)),
                'entry_validity_hours': params.get('entry_validity_hours', DEFAULT_PARAMS.get('entry_validity_hours', 12.0)),
                'pullback_rsi_long': params.get('pullback_rsi_long', DEFAULT_PARAMS.get('pullback_rsi_long', 35)),
                'pullback_rsi_short': params.get('pullback_rsi_short', DEFAULT_PARAMS.get('pullback_rsi_short', 65)),
                'max_adds': params.get('max_adds', DEFAULT_PARAMS.get('max_adds', 1))
            }
            
            # [CHART] 디버깅 로그
            if params.get('trend_interval') == '1d' and params.get('atr_mult') == 1.5:
                logger.info(f"[CHART] [OPT] entry_cost={entry_cost:.4f}, atr_mult={backtest_params['atr_mult']}, trail_start_r={backtest_params['trail_start_r']}, trail_dist_r={backtest_params['trail_dist_r']}")
            
            # 전략 실행 시 전달할 파라미터
            # X7PlusStrategy.run_backtest_plus에 filter_tf 전달
            backtest_params['filter_tf'] = filter_tf
            
            # 백테스트 실행 (Core Interface)
            if hasattr(strategy, 'run_backtest') and not hasattr(strategy, 'run_backtest_plus'):
                # AlphaX7Core
                trades = strategy.run_backtest(
                    df_pattern=df_pattern,
                    df_entry=df_entry,  # [FIX] 원본 15min 데이터 사용
                    slippage=entry_cost,  # [v7.26] 진입 비용 전달
                    atr_mult=backtest_params.get('atr_mult'),
                    trail_start_r=backtest_params.get('trail_start_r'),
                    trail_dist_r=backtest_params.get('trail_dist_r'),
                    pattern_tolerance=backtest_params.get('pattern_tolerance'),
                    entry_validity_hours=backtest_params.get('entry_validity_hours'),
                    pullback_rsi_long=backtest_params.get('pullback_rsi_long'),
                    pullback_rsi_short=backtest_params.get('pullback_rsi_short'),
                    max_adds=backtest_params.get('max_adds'),
                    filter_tf=filter_tf,
                    rsi_period=params.get('rsi_period', DEFAULT_PARAMS['rsi_period']),
                    atr_period=params.get('atr_period', DEFAULT_PARAMS['atr_period']),
                    macd_fast=params.get('macd_fast', DEFAULT_PARAMS['macd_fast']),
                    macd_slow=params.get('macd_slow', DEFAULT_PARAMS['macd_slow']),
                    macd_signal=params.get('macd_signal', DEFAULT_PARAMS['macd_signal']),
                    ema_period=params.get('ema_period', DEFAULT_PARAMS['ema_period']),
                    enable_pullback=params.get('enable_pullback', DEFAULT_PARAMS['enable_pullback'])  # v7.30 SSOT
                )

            else:
                # Legacy Strategy
                backtest_params['filter_tf'] = filter_tf
                trades = strategy.run_backtest_plus(**backtest_params)
            
            # [DEBUG] 거래 수 확인
            # logger.info(f"[DEBUG-OPT] 거래 수: {len(trades) if trades else 0}개")
            
            # [FIX] 10개는 너무 가혹함 (최소 거래수 파라미터화)
            min_trades = params.get('min_trades', 3)
            if not trades or len(trades) < min_trades:
                return None
            
            # 1. 방향 필터링
            if direction != 'Both':
                trades = [t for t in trades if t['type'] == direction]
                if len(trades) < 3: return None
            
            # [FIX] Option 2: 레버리지 자동 최적화 (MDD 타겟 맞춤)
            # 2. 레버리지 적용 (그리드에 설정된 정수 배율 사용)
            max_mdd_limit = params.get('max_mdd', 20.0)
            if isinstance(max_mdd_limit, list): max_mdd_limit = max_mdd_limit[0]
            
            # 그리드에서 넘어온 레버리지 (항상 정수여야 함)
            grid_leverage = int(leverage)
            
            # 레버리지 적용 (PnL 수정)
            for t in trades:
                t['pnl'] = t['pnl'] * grid_leverage
            
            # 메트릭 계산 (레버리지 반영됨)
            metrics = self._calculate_metrics(trades)
            
            # [FIX] 레버리지 적용 후 MDD가 한도를 초과하면 탈락 (max_mdd가 100이면 사실상 무시)
            if max_mdd_limit < 100.0 and abs(metrics['max_drawdown']) > max_mdd_limit:
                return None

            # 등급 할당 (균형형 기준으로 임시 등급 부여)
            grade = assign_grade_by_preset(
                preset_type='balanced',
                metrics={
                    'win_rate': metrics['win_rate'],
                    'profit_factor': metrics['profit_factor'],
                    'mdd': metrics['max_drawdown'],
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'compound_return': metrics['compound_return']
                }
            )

            return OptimizationResult(
                params=params,
                trades=len(trades),
                win_rate=metrics['win_rate'],
                total_return=metrics['total_return'],
                simple_return=metrics['simple_return'],
                compound_return=metrics['compound_return'],
                max_drawdown=metrics['max_drawdown'],
                sharpe_ratio=metrics['sharpe_ratio'],
                profit_factor=metrics['profit_factor'],
                avg_trades_per_day=metrics.get('avg_trades_per_day', 0.0),
                stability=metrics.get('stability', "[WARNING]"),
                grade=grade,
                avg_pnl=metrics.get('avg_pnl', 0.0),
                cagr=metrics.get('cagr', 0.0)
            )
            
        except Exception as e:
            logger.warning(f" [WARNING] 백테스트 오류: {e}")
            return None
    
    # calculate_mdd() 삭제 (v7.30) → utils.metrics.calculate_mdd() 사용 (SSOT)

    @staticmethod
    def calculate_metrics(trades: List[Dict]) -> Dict:
        """
        거래 결과에서 메트릭 계산 (SSOT 완전 통합 v7.24)

        ===========================================================
        [CHART] 지표 계산 공식 (METRICS CALCULATION FORMULAS)
        ===========================================================

        1. win_rate (승률)
           공식: (수익 거래 수 / 전체 거래 수) × 100
           영향: filter_tf↑ → 승률↑, atr_mult↑ → 승률↑

        2. simple_return (단리 수익률)
           공식: Σ(각 거래의 PnL%)
           영향: leverage↑ → 수익↑, trail_start_r↑ → 수익↑

        3. compound_return (복리 수익률)
           공식: (Π(1 + PnL%/100) - 1) × 100
           영향: leverage↑ → 수익↑↑ (복리 효과)

        4. max_drawdown (MDD, 최대 낙폭)
           공식: max((peak - current) / peak × 100)
           영향: leverage↑ → MDD↑, atr_mult↑ → MDD↑

        5. sharpe_ratio (샤프 비율)
           공식: (평균 수익 / 표준편차) × √(252 × 4)
           영향: leverage↑ → 변동성↑ → 샤프↓

        6. profit_factor (수익 팩터)
           공식: 총 수익 / 총 손실
           영향: 전체 파라미터의 복합 효과
        ===========================================================

        Note:
            v7.24부터 utils.metrics.calculate_backtest_metrics()를 직접 호출합니다.
            클램핑 없이 실제 PnL을 사용하여 정확한 메트릭을 계산합니다.
            이는 MetaOptimizer와 동일한 방식이며, SSOT 원칙을 완전히 준수합니다.
        """
        if not trades:
            return {k: 0 for k in ['win_rate', 'total_return', 'simple_return', 'compound_return', 'max_drawdown', 'sharpe_ratio', 'profit_factor']}

        # [OK] SSOT 직접 호출 (클램핑 없음)
        from utils.metrics import calculate_backtest_metrics

        metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

        # 키 이름 변환 (하위 호환성 유지)
        result = {
            'win_rate': round(metrics['win_rate'], 2),
            'total_pnl': round(metrics['total_pnl'], 2),
            'simple_return': round(metrics['total_pnl'], 2),
            'compound_return': round(metrics['compound_return'], 2),
            'mdd': round(metrics['mdd'], 2),
            'sharpe_ratio': round(metrics['sharpe_ratio'], 2),
            'profit_factor': round(metrics['profit_factor'], 2),
            'stability': metrics['stability'],
            'avg_trades_per_day': metrics['avg_trades_per_day'],
            'avg_pnl': round(metrics['avg_pnl'], 4),
            'cagr': round(metrics['cagr'], 2)
        }

        # 하위 호환성: alias 제공 (Deprecated)
        result['total_return'] = result['total_pnl']  # Deprecated: use 'total_pnl'
        result['max_drawdown'] = result['mdd']  # Deprecated: use 'mdd'

        return result

    @staticmethod
    def _calculate_cagr(final_equity: float, trades: List[Dict]) -> float:
        """
        연간 복리 성장률(CAGR) 계산

        Wrapper for utils.metrics.calculate_cagr() (SSOT)
        """
        from utils.metrics import calculate_cagr
        return calculate_cagr(trades, final_capital=final_equity, initial_capital=1.0)

    def _calculate_metrics(self, trades: List[Dict]) -> Dict:
        """인스턴스용 하위 호환 메서드"""
        return self.calculate_metrics(trades)

    def _calculate_stability(self, pnls: List[float]) -> str:
        """
        3구간 안정성 체크 (과거/중간/최근)

        Wrapper for utils.metrics.calculate_stability() (SSOT)
        """
        from utils.metrics import calculate_stability
        return calculate_stability(pnls)

    def _classify_results(self, results: List[OptimizationResult], mode: str = 'standard') -> List[OptimizationResult]:
        """
        결과를 클러스터링하여 유형별 대표값 선정 (v3 개선)
        
        Args:
            results: 최적화 결과 리스트
            mode: 'quick' (1개), 'standard' (3개), 'deep' (5개+)
        
        Returns:
            대표 결과 리스트
        """
        if not results:
            return []
        
        # 결과 복사 및 정렬 기준별 필터링
        representatives = []
        seen_params = set()

        def add_rep(res, label):
            param_key = str(res.params)
            if param_key not in seen_params:
                res.strategy_type = label
                # 프리셋 타입에 맞게 등급 재할당
                res.grade = assign_grade_by_preset(
                    preset_type=label,
                    metrics={
                        'win_rate': res.win_rate,
                        'profit_factor': res.profit_factor,
                        'mdd': res.max_drawdown,
                        'sharpe_ratio': res.sharpe_ratio,
                        'compound_return': res.compound_return
                    }
                )
                representatives.append(res)
                seen_params.add(param_key)
        
        def add_multiple_reps(sorted_results, label_prefix, count):
            """상위 N개 결과를 추가 (중복 제외)"""
            added = 0
            for i, res in enumerate(sorted_results):
                if added >= count:
                    break
                param_key = str(res.params)
                if param_key not in seen_params:
                    res.strategy_type = f"{label_prefix}#{added+1}"
                    # 프리셋 타입에 맞게 등급 재할당
                    res.grade = assign_grade_by_preset(
                        preset_type=label_prefix, # "[FIRE]공격" 등
                        metrics={
                            'win_rate': res.win_rate,
                            'profit_factor': res.profit_factor,
                            'mdd': res.max_drawdown,
                            'sharpe_ratio': res.sharpe_ratio,
                            'compound_return': res.compound_return
                        }
                    )
                    representatives.append(res)
                    seen_params.add(param_key)
                    added += 1

        profitable = [r for r in results if r.total_return > 0]
        
        # ===== Quick 모드: 1개 (최고 스코어) =====
        if mode == 'quick':
            # 복합 스코어 기준 최고 1개
            best = max(results, key=lambda x: (
                x.win_rate * 1.0 + 
                (100 - abs(x.max_drawdown)) * 0.5 + 
                x.sharpe_ratio * 2.0
            ))
            add_rep(best, "[TROPHY]최적")
            return representatives
        
        # ===== Standard 모드: 3개 (공격, 균형, 보수) =====
        if mode == 'standard':
            # 1. [FIRE]공격형: 최고 수익률
            aggressive = max(results, key=lambda x: x.compound_return)
            add_rep(aggressive, "[FIRE]공격")
            
            # 2. 균형형: 최고 샤프 지수
            balanced = max(results, key=lambda x: x.sharpe_ratio)
            add_rep(balanced, "균형")
            
            # 3. 보수형: 최저 MDD (수익 > 0 중)
            if profitable:
                conservative = min(profitable, key=lambda x: abs(x.max_drawdown))
                add_rep(conservative, "보수")
            
            return representatives
        
        # ===== Deep 모드: 5개+ (공격×3, 균형, 보수) =====
        # 1. [FIRE]공격형 Top 3: 최고 수익률 상위 3개
        sorted_by_return = sorted(results, key=lambda x: x.compound_return, reverse=True)
        add_multiple_reps(sorted_by_return, "[FIRE]공격", 3)
        
        # 2. 균형형: 최고 샤프 지수
        balanced = max(results, key=lambda x: x.sharpe_ratio)
        add_rep(balanced, "균형")
        
        # 3. 보수형: 최저 MDD (수익 > 0 중)
        if profitable:
            conservative = min(profitable, key=lambda x: abs(x.max_drawdown))
            add_rep(conservative, "보수")
        
        # 4. [TARGET]고승률형: 최고 승률
        high_wr = max(results, key=lambda x: x.win_rate)
        add_rep(high_wr, "[TARGET]고승률")
        
        # 5. 저빈도형: 일평균 거래 가장 적은 것 (수익 > 0)
        if profitable:
            low_freq = min(profitable, key=lambda x: getattr(x, 'avg_trades_per_day', x.trades / 30))
            add_rep(low_freq, "저빈도")
        
        return representatives
    
    def get_best(self, n: int = 10) -> List[OptimizationResult]:
        """상위 N개 결과 반환"""
        return self.results[:n]
    
    def analyze_top_results(self, n: int = 100, threshold: float = 0.85) -> Dict:
        """
        상위 결과 분석 → 지배적 파라미터 고정 및 범위 축소 (Iterative Optimization용)
        
        Args:
            n: 분석할 상위 결과 수
            threshold: 고정 판단 임계값 (예: 0.85 -> 85% 이상 같은 값이면 고정)
            
        Returns:
            Dict: 축소된 파라미터 그리드
        """
        if not self.results:
            return {}
            
        from collections import Counter
        top_results = sorted(self.results, key=lambda x: getattr(x, 'sharpe_ratio', 0), reverse=True)[:n]
        
        # 분석 대상 파라미터 (지표 관련)
        target_params = ['atr_mult', 'trail_start_r', 'trail_dist_r', 'pattern_tolerance', 'entry_validity_hours', 'pullback_rsi_long', 'pullback_rsi_short', 'filter_tf', 'entry_tf', 'leverage']

        
        fixed_params = {}
        reduced_ranges = {}
        
        for param in target_params:
            # 해당 파라미터 값 추출
            values = []
            for res in top_results:
                val = res.params.get(param)
                if val is not None:
                    if isinstance(val, list): val = val[0]
                    values.append(val)
            
            if not values: continue
            
            # 빈도 분석
            counts = Counter(values)
            most_common_val, count = counts.most_common(1)[0]
            ratio = count / len(values)
            
            if ratio >= threshold:
                # 지배적인 값 발견 -> 고정
                fixed_params[param] = [most_common_val]
                logger.info(f"[PIN] [OPT-ADAPT] '{param}' fixed to {most_common_val} (Dominance: {ratio:.1%})")
            else:
                # 분포 분석 -> 범위 축소 (최소~최대값 사이를 다시 촘촘하게)
                min_v = min(values)
                max_v = max(values)
                
                # 기존 INDICATOR_RANGE나 원본 그리드에서 해당 구간의 값들 추출
                # 여기서는 간단히 5분할하여 촘촘하게 생성
                if isinstance(min_v, (int, float)) and not isinstance(min_v, bool):
                     # 수치형 파라미터
                     step = (max_v - min_v) / 5
                     if step > 0:
                         new_vals = [round(min_v + step * i, 3) for i in range(6)]
                         reduced_ranges[param] = sorted(list(set(new_vals)))
                     else:
                         reduced_ranges[param] = [min_v]
                else:
                    # 카테고리형 (filter_tf 등)
                    reduced_ranges[param] = sorted(list(set(values)))
                
                logger.debug(f"[SEARCH] [OPT-ADAPT] '{param}' range narrowed: {min_v} ~ {max_v}")

        # 새로운 그리드 생성
        new_grid = {}
        # 1. 고정된 값 적용
        new_grid.update(fixed_params)
        # 2. 축소된 범위 적용
        new_grid.update(reduced_ranges)
        
        # 3. 공통 필드 유지 (trend_interval, max_mdd 등)
        if self.results:
            first_params = self.results[0].params
            for k in ['trend_interval', 'max_mdd', 'direction']:
                if k not in new_grid and k in first_params:
                    val = first_params[k]
                    new_grid[k] = val if isinstance(val, list) else [val]
        
        return new_grid

    def filter_unique_results(self, results: Optional[List[OptimizationResult]] = None, 
                              max_count: int = 30) -> List[OptimizationResult]:
        """
        중복/유사 결과 제거 + 상위 N개 선택
        
        기준:
        - 승률 1% 이내 + MDD 2% 이내 = 유사 결과
        - 유사 그룹 내 → 복합 스코어 높은 1개만
        - 최종 max_count개 반환
        """
        if results is None:
            results = self.results
        
        if not results:
            return []
        
        # 복합 스코어 계산 (승률 > MDD > 샤프 > 수익률)
        def calc_score(r):
            return (
                r.win_rate * 1.0 +                    # 승률 88% → 88점
                (100 + r.max_drawdown) * 0.5 +        # MDD -17% → 41.5점
                r.sharpe_ratio * 2.0 +                # 샤프 26 → 52점
                min(r.total_return / 100, 50) * 0.2   # 수익률 cap 50
            )
        
        # 스코어 순 정렬
        scored = sorted(results, key=calc_score, reverse=True)
        
        # 유사 결과 제거
        unique = []
        for r in scored:
            is_duplicate = False
            for u in unique:
                # MDD는 보통 음수이므로 abs()로 차이 확인
                if (abs(r.win_rate - u.win_rate) < 1.0 and
                    abs(r.max_drawdown - u.max_drawdown) < 2.0):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(r)
            
            if len(unique) >= max_count:
                break
        
        logger.info(f"[RELOAD] [FILTER] {len(results)} → {len(unique)} (중복 제거)")
        return unique

    def to_dataframe(self) -> pd.DataFrame:
        """결과를 DataFrame으로 변환"""
        if not self.results:
            return pd.DataFrame()
        
        rows = []
        for r in self.results:
            row = {**r.params}
            row['trades'] = r.trades
            row['win_rate'] = r.win_rate
            row['total_return'] = r.total_return
            row['max_drawdown'] = r.max_drawdown
            row['sharpe_ratio'] = r.sharpe_ratio
            row['profit_factor'] = r.profit_factor
            rows.append(row)
        
        return pd.DataFrame(rows)

    # ==================== v7.22: Coarse-to-Fine API ====================

    def run_coarse_grid_optimization(
        self,
        df: pd.DataFrame,
        trend_tf: str,
        metric: str = 'sharpe_ratio',
        n_cores: Optional[int] = None
    ) -> List[OptimizationResult]:
        """
        Coarse Grid 최적화 (넓은 범위 탐색)

        3³ × 3 × 3 = 243개 조합:
        - atr_mult: [1.0, 2.0, 3.0]
        - filter_tf: ['4h', '12h', '1d']
        - trail_start_r: [1.0, 2.0, 3.0]
        - trail_dist_r: [0.015, 0.020, 0.030]
        - entry_validity_hours: [6, 48, 96]

        Args:
            df: 백테스트 데이터
            trend_tf: 추세 타임프레임
            metric: 최적화 메트릭 ('sharpe_ratio', 'profit_factor', 등)
            n_cores: CPU 코어 수 (None이면 자동)

        Returns:
            OptimizationResult 리스트 (정렬됨)
        """
        logger.info(f"[SEARCH] [Coarse] Starting Coarse Grid optimization...")

        # v7.23: 거래소별 수수료 및 파라미터 범위 자동 조정
        from config.constants.trading import get_total_cost
        from config.parameters import (
            get_atr_range_by_exchange,
            get_filter_tf_range_by_exchange
        )

        # 1. 거래소별 수수료 계산
        total_cost = get_total_cost(self.exchange)

        # 2. 거래소별 파라미터 범위
        atr_range = get_atr_range_by_exchange(self.exchange, mode='coarse')
        filter_range = get_filter_tf_range_by_exchange(self.exchange, mode='coarse')

        logger.info(f"[CHART] [{self.exchange.upper()}] Total Cost: {total_cost*100:.3f}%")
        logger.info(f"  ATR Range: {atr_range}")
        logger.info(f"  Filter Range: {filter_range}")

        # Coarse Grid 정의 (거래소별 조정)
        # MACD: len(atr_range) × len(filter_range) × 3 × 3 × 3 조합
        # ADX: 위 조합 × 3 × 3 추가
        coarse_grid = {
            'trend_interval': [trend_tf],
            'atr_mult': atr_range,           # 거래소별 범위
            'filter_tf': filter_range,        # 거래소별 범위
            'trail_start_r': [1.0, 2.0, 3.0],
            'trail_dist_r': [0.015, 0.020, 0.030],
            'entry_validity_hours': [6.0, 48.0, 96.0],
            'slippage': [total_cost],         # 거래소별 수수료
            'fee': [0]  # slippage에 이미 포함되어 있으므로 0으로 설정
        }

        # ADX 전략이면 ADX 파라미터 추가
        if self.strategy_type == 'adx':
            coarse_grid['adx_period'] = [10, 14, 18]         # 3개 (빠름, 표준, 느림)
            coarse_grid['adx_threshold'] = [20.0, 25.0, 30.0]  # 3개 (Wilder 1978 표준 범위 25±5)

        # 조합 수 확인
        import itertools
        combinations = list(itertools.product(
            *[coarse_grid[k] for k in coarse_grid.keys()]
        ))
        logger.info(f"[CHART] [Coarse] Grid size: {len(combinations)} combinations")

        # [WARNING] WORKAROUND: 임시로 필터 값을 완화한 후 실행
        from config import parameters
        original_filter = parameters.OPTIMIZATION_FILTER.copy()

        # 필터 완전 비활성화
        parameters.OPTIMIZATION_FILTER = {
            'min_win_rate': 0.0,
            'max_mdd': 999.0,
            'min_total_return': -9999.0,
            'min_trades_per_day': 0.0,
            'min_absolute_trades': 0
        }
        logger.info(f"[WARNING] [Coarse] Filter temporarily disabled")

        try:
            # 기존 run_optimization 호출
            results = self.run_optimization(
                df=df,
                grid=coarse_grid,
                metric=metric,
                n_cores=n_cores,
                mode='coarse',  # ← 'coarse' 모드 사용 (분류 건너뛰기)
                skip_filter=True  # ← [FIX] 필터 완전 우회 (라인 1808 완화와 일관성)
            )
        finally:
            # 필터 복원
            parameters.OPTIMIZATION_FILTER = original_filter
            logger.info(f"[CHECK] [Coarse] Filter restored")

        logger.info(f"[CHECK] [Coarse] Complete: {len(results)} results")
        return results

    def run_fine_grid_optimization(
        self,
        df: pd.DataFrame,
        trend_tf: str,
        coarse_results: List[OptimizationResult],
        top_n: int = 20,
        metric: str = 'sharpe_ratio',
        n_cores: Optional[int] = None
    ) -> List[OptimizationResult]:
        """
        Fine Grid 최적화 (정밀 탐색)

        coarse_results 상위 top_n개에서 백분위수 추출:
        - 10~90% 범위로 3단계 그리드 생성
        - 약 27개 조합 (3³)

        Args:
            df: 백테스트 데이터
            trend_tf: 추세 타임프레임
            coarse_results: Coarse Grid 결과
            top_n: 상위 N개 사용 (기본값 20, 전체의 ~8%)
            metric: 최적화 메트릭
            n_cores: CPU 코어 수

        Returns:
            OptimizationResult 리스트 (정렬됨)
        """
        logger.info(f"[TARGET] [Fine] Starting Fine Grid optimization...")

        if not coarse_results:
            logger.warning(f"[NO] [Fine] No coarse results provided")
            return []

        # 상위 N개 추출
        top_results = coarse_results[:top_n]
        logger.info(f"[CHART] [Fine] Analyzing top {len(top_results)} results...")

        # 백분위수 기반 범위 추출
        fine_grid = self._extract_fine_ranges(top_results, trend_tf)

        # 조합 수 확인
        import itertools
        combinations = list(itertools.product(
            *[fine_grid[k] for k in fine_grid.keys()]
        ))
        logger.info(f"[CHART] [Fine] Grid size: {len(combinations)} combinations")

        # 기존 run_optimization 호출
        # [FIX] v7.22.1: Fine Grid도 필터 완화 (ADX 전략 지원)
        from config import parameters
        original_filter = parameters.OPTIMIZATION_FILTER.copy()

        # 필터 완화 (Fine Grid는 Coarse보다 약간 엄격)
        parameters.OPTIMIZATION_FILTER = {
            'min_win_rate': 70.0,  # 70% 이상
            'max_mdd': 30.0,       # 30% 이하
            'min_total_return': 0.0,  # 0% 이상
            'min_trades_per_day': 0.3,  # 0.3회/일 이상
            'min_absolute_trades': 5  # 최소 5개
        }

        try:
            results = self.run_optimization(
                df=df,
                grid=fine_grid,
                metric=metric,
                n_cores=n_cores,
                mode='standard',
                skip_filter=False  # 완화된 필터 사용
            )
        finally:
            # 필터 복원
            parameters.OPTIMIZATION_FILTER = original_filter

        logger.info(f"[CHECK] [Fine] Complete: {len(results)} results")
        return results

    def _extract_fine_ranges(
        self,
        top_results: List[OptimizationResult],
        trend_tf: str
    ) -> Dict:
        """
        상위 결과에서 백분위수 기반 Fine Grid 범위 추출

        Args:
            top_results: 상위 결과 리스트
            trend_tf: 추세 타임프레임

        Returns:
            Fine Grid 딕셔너리 (3개 값씩)
        """
        from collections import Counter

        # 파라미터별 값 수집
        atr_mults = [r.params.get('atr_mult', 1.5) for r in top_results]
        trail_starts = [r.params.get('trail_start_r', 1.0) for r in top_results]
        trail_dists = [r.params.get('trail_dist_r', 0.02) for r in top_results]
        entry_hours = [r.params.get('entry_validity_hours', 6.0) for r in top_results]
        filter_tfs = [r.params.get('filter_tf', '4h') for r in top_results]

        # ADX 파라미터 수집 (ADX 전략인 경우만)
        adx_periods = [r.params.get('adx_period', 14) for r in top_results if 'adx_period' in r.params]
        adx_thresholds = [r.params.get('adx_threshold', 25.0) for r in top_results if 'adx_threshold' in r.params]

        # 수치형: 10~90% 백분위수 (3단계)
        def percentile_range(values: List[float], steps: int = 3) -> List[float]:
            if not values:
                return []
            p10 = float(np.percentile(values, 10))
            p90 = float(np.percentile(values, 90))
            if p10 == p90:
                # [OK] FIX v7.22.1: 수렴 시 ±20% 범위로 확장 (국소 탐색)
                center = p10
                if center > 0:
                    # 양수면 비율 기반 확장
                    return [float(x) for x in np.linspace(center * 0.8, center * 1.2, steps)]
                else:
                    # 0 근처면 절대값 기반 확장
                    return [float(x) for x in np.linspace(center - 0.2, center + 0.2, steps)]
            return [float(x) for x in np.linspace(p10, p90, steps)]

        # 카테고리형: 빈도 상위 3개
        def top_categories(values: List[str], top_k: int = 3) -> List[str]:
            counts = Counter(values)
            return [v for v, _ in counts.most_common(top_k)]

        fine_grid = {
            'trend_interval': [trend_tf],
            'atr_mult': percentile_range(atr_mults, 3),
            'filter_tf': top_categories(filter_tfs, 3),
            'trail_start_r': percentile_range(trail_starts, 3),
            'trail_dist_r': percentile_range(trail_dists, 3),
            'entry_validity_hours': percentile_range(entry_hours, 3)
        }

        # v7.23: 거래소별 수수료 적용 (Coarse와 일관성 보장)
        from config.constants.trading import get_total_cost
        total_cost = get_total_cost(self.exchange)
        fine_grid['slippage'] = [total_cost]
        fine_grid['fee'] = [0]

        # ADX 파라미터 추가 (ADX 전략인 경우)
        if adx_periods and adx_thresholds:
            fine_grid['adx_period'] = percentile_range(adx_periods, 3)
            fine_grid['adx_threshold'] = percentile_range(adx_thresholds, 3)

        logger.info(f"[CHART] [Fine] Extracted ranges:")
        for k, v in fine_grid.items():
            if k != 'trend_interval':
                logger.info(f"  {k}: {v}")

        return fine_grid


# 테스트
if __name__ == "__main__":
    # [OK] v7.28: 멀티프로세싱 스타트 메서드 명시 (Windows 호환성)
    import multiprocessing as mp
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        # 이미 설정된 경우 무시
        pass

    import os
    import sys
    import pandas as pd
    import traceback

    try:
        # 1. 경로 설정
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
        
        from core.strategy_core import AlphaX7Core
        
        # 데이터 로드 (Parquet 우선 탐색)
        csv_path = os.path.join(BASE_DIR, 'data', 'cache', 'bybit_btcusdt_15m.parquet')
        if not os.path.exists(csv_path):
            csv_path = os.path.join(BASE_DIR, 'data', 'bybit_BTCUSDT_15m.csv') # Fallback
            
        logger.info(f"[CHART] Testing with: {csv_path}")
        
        if os.path.exists(csv_path):
            if csv_path.endswith('.parquet'):
                df = pd.read_parquet(csv_path)
            else:
                df = pd.read_csv(csv_path)
                
            # 타임스탬프 변환
            if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                first_ts = df['timestamp'].iloc[0]
                val = float(first_ts)
                if val > 1e12:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                elif val > 1e8:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 최근 5000개만 사용 (테스트용)
            df = df.tail(5000).reset_index(drop=True)
            logger.info(f"Loaded {len(df)} candles. Range: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")
            
            # 1. 최적화 엔진 시작
            optimizer = BacktestOptimizer(AlphaX7Core, df)
            grid = generate_fast_grid('1h')
            
            logger.info(f"[ROCKET] [Stage 1] Fast Grid Search Starting...")
            results = optimizer.run_optimization(df, grid, metric='sharpe_ratio')
            logger.info(f"[OK] Found {len(results)} combinations.")
            
            # 2. 분석 및 범위 축소 (신규 기능 테스트)
            refined_grid = optimizer.analyze_top_results(n=10, threshold=0.7)
            
            # 3. 2단계 정밀 최적화
            if refined_grid:
                logger.info(f"[SPARKLE] [Analysis] Refined Grid calculated: {refined_grid}")
                logger.info(f"[ROCKET] [Stage 2] Iterative Scan Starting...")
                refined_results = optimizer.run_optimization(df, refined_grid, metric='sharpe_ratio')
                logger.info(f"[TROPHY] Final Best Results: {len(refined_results)}")
                
                for res in refined_results[:5]:
                    logger.info(f" - {res.params}: Sharpe={res.sharpe_ratio:.2f}, WR={res.win_rate:.1f}%")
            else:
                logger.info("[SPARKLE] [Analysis] No dominant patterns found to refine.")
        else:
            logger.error(f"[NO] No test data found at {csv_path}. Please download data first.")
            
    except Exception:
        logger.info("[NO] Test failed with error:")
        traceback.print_exc()
