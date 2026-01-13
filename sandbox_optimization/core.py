"""
샌드박스 전략 코어 (레거시 호환용 Wrapper)
==========================================

⚠️ DEPRECATED: 이 모듈은 레거시 호환을 위해 유지됩니다.
   신규 코드에서는 strategies/ 모듈을 직접 사용하세요.

기존 코드:
    from sandbox_optimization.core import run_backtest, run_optimization
    result = run_backtest(df, params, timeframe='1h', method='macd')

신규 코드 (권장):
    from sandbox_optimization.strategies import MACDStrategy
    strategy = MACDStrategy(params)
    result = strategy.backtest(df, timeframe='1h')
"""

import warnings
from typing import Dict, List

import pandas as pd

# 실제 구현은 base.py와 strategies/에서 가져옴
from .base import (
    calculate_indicators,
    prepare_data,
    run_backtest_core,
)
from .strategies.macd import MACDStrategy
from .strategies.adxdi import ADXDIStrategy
from .presets import SANDBOX_PARAMS
from .constants import DEFAULT_SLIPPAGE, DEFAULT_FEE


# =============================================================================
# 패턴 탐지 함수 (레거시 호환)
# =============================================================================
def detect_patterns_macd(
    df: pd.DataFrame,
    tolerance: float = 0.10,
    min_adx: float = 10,
    min_vol_ratio: float = 0.0,
) -> List[Dict]:
    """
    MACD 히스토그램 기반 W/M 패턴 탐지 (레거시 호환)
    
    ⚠️ DEPRECATED: MACDStrategy.detect_patterns() 사용 권장
    """
    params = {
        'tolerance': tolerance,
        'adx_min': min_adx,
        'min_vol_ratio': min_vol_ratio,
    }
    strategy = MACDStrategy(params)
    return strategy.detect_patterns(df)


def detect_patterns_adxdi(
    df: pd.DataFrame,
    tolerance: float = 0.10,
    min_adx: float = 10,
    min_vol_ratio: float = 0.0,
) -> List[Dict]:
    """
    ADX/DI 기반 W/M 패턴 탐지 (레거시 호환)
    
    ⚠️ DEPRECATED: ADXDIStrategy.detect_patterns() 사용 권장
    """
    params = {
        'tolerance': tolerance,
        'adx_min': min_adx,
        'min_vol_ratio': min_vol_ratio,
    }
    strategy = ADXDIStrategy(params)
    return strategy.detect_patterns(df)


# =============================================================================
# 메인 백테스트 함수 (레거시 호환)
# =============================================================================
def run_backtest(
    df: pd.DataFrame,
    params: Dict = None,
    timeframe: str = '2h',
    method: str = 'macd',
    slippage: float = DEFAULT_SLIPPAGE,
    fee: float = DEFAULT_FEE,
    apply_filters: bool = True,
) -> Dict:
    """
    통합 백테스트 실행 (레거시 호환)
    
    ⚠️ DEPRECATED: MACDStrategy.backtest() 또는 ADXDIStrategy.backtest() 사용 권장
    
    Args:
        df: 15m 데이터프레임
        params: 파라미터 딕셔너리
        timeframe: '1h', '2h', '4h', etc.
        method: 'macd' 또는 'adxdi'
        apply_filters: 필터 적용 여부
    """
    if params is None:
        params = SANDBOX_PARAMS.copy()
    
    # 전략 선택
    if method == 'adxdi':
        strategy = ADXDIStrategy(params)
    else:
        strategy = MACDStrategy(params)
    
    # 백테스트 실행
    result = strategy.backtest(
        df, 
        timeframe=timeframe, 
        apply_filters=apply_filters,
        slippage=slippage,
        fee=fee,
    )
    
    # 레거시 호환을 위한 필드 추가
    result['method'] = method
    
    return result


# =============================================================================
# 최적화 함수 (레거시 호환)
# =============================================================================
def run_optimization(
    df: pd.DataFrame,
    timeframe: str = '2h',
    method: str = 'macd',
    mode: str = 'quick',
    apply_filters: bool = True,
    verbose: bool = True,
) -> List[Dict]:
    """
    그리드 서치 최적화 (레거시 호환)
    
    ⚠️ DEPRECATED: MACDStrategy.optimize() 또는 ADXDIStrategy.optimize() 사용 권장
    
    Args:
        mode: 'quick', 'default', 'deep'
        apply_filters: 필터 적용 여부
    """
    # 전략 선택
    if method == 'adxdi':
        strategy = ADXDIStrategy()
    else:
        strategy = MACDStrategy()
    
    # 최적화 실행
    results = strategy.optimize(
        df,
        timeframe=timeframe,
        mode=mode,
        apply_filters=apply_filters,
        verbose=verbose,
    )
    
    # 레거시 호환을 위한 필드 추가
    for r in results:
        r['method'] = method
    
    return results


# =============================================================================
# 레거시 호환을 위해 export
# =============================================================================
__all__ = [
    'calculate_indicators',
    'detect_patterns_macd',
    'detect_patterns_adxdi',
    'run_backtest_core',
    'run_backtest',
    'run_optimization',
]
