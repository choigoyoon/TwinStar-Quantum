"""
샌드박스 최적화 모듈 v1.2.0
===========================

두 가지 패턴 탐지 전략을 독립 모듈로 분리

모듈 구조:
    sandbox_optimization/
    ├── __init__.py          # 패키지 API
    ├── constants.py         # 비용 상수, 기본값
    ├── presets.py           # 파라미터 프리셋
    ├── filters.py           # 진입 필터 (Stochastic, Downtrend)
    ├── base.py              # 공통 로직 (지표, 백테스트 코어)
    ├── interface.py         # UI 연결용 인터페이스
    ├── core.py              # 레거시 호환 (deprecated)
    └── strategies/
        ├── __init__.py
        ├── macd.py          # MACD 전략 (독립)
        └── adxdi.py         # ADX/DI 전략 (독립)

사용법:
    # 방법 1: 기존 방식 (레거시 호환)
    from sandbox_optimization import run_backtest, SANDBOX_PARAMS
    result = run_backtest(df, SANDBOX_PARAMS, timeframe='1h', method='macd')
    
    # 방법 2: 전략 클래스 직접 사용
    from sandbox_optimization.strategies import MACDStrategy, ADXDIStrategy
    macd = MACDStrategy(params)
    result = macd.backtest(df, timeframe='1h')
    
    # 방법 3: UI 인터페이스 사용
    from sandbox_optimization.interface import run_strategy, compare_strategies
    result = run_strategy(df, strategy='macd', timeframe='1h')
"""

__version__ = '1.2.0'

# =============================================================================
# 상수
# =============================================================================
from .constants import (
    DEFAULT_SLIPPAGE,
    DEFAULT_FEE,
    INITIAL_CAPITAL,
    TOTAL_COST_ONE_WAY,
    TOTAL_COST_ROUND_TRIP,
    DEFAULT_TIMEFRAME,
    DEFAULT_METHOD,
    AVAILABLE_TIMEFRAMES,
    AVAILABLE_METHODS,
    calculate_grade,
)

# =============================================================================
# 프리셋
# =============================================================================
from .presets import (
    SANDBOX_PARAMS,
    HYBRID_OPTIMAL_PARAMS,
    LOCAL_V23_PARAMS,
    MAX_PROFIT_PARAMS,
    FILTER_ATR_OPTIMAL,
    BALANCED_OPTIMAL,
    STABLE_OPTIMAL,
    ALL_PRESETS,
    get_preset,
    list_presets,
    load_preset_json,
    save_preset_json,
    get_preset_description,
)

# =============================================================================
# 필터
# =============================================================================
from .filters import SignalFilter, apply_filters

# =============================================================================
# 공통 기반 (base.py)
# =============================================================================
from .base import (
    calculate_indicators,
    prepare_data,
    run_backtest_core,
    BaseStrategy,
)

# =============================================================================
# 전략 클래스 (strategies/)
# =============================================================================
from .strategies import (
    MACDStrategy,
    ADXDIStrategy,
    get_strategy,
    list_strategies,
)

from .strategies.macd import run_macd_backtest, run_macd_optimization
from .strategies.adxdi import run_adxdi_backtest, run_adxdi_optimization

# =============================================================================
# UI 인터페이스
# =============================================================================
from .interface import (
    run_strategy,
    compare_strategies,
    optimize_strategy,
    get_available_options,
    format_result_summary,
    format_comparison_summary,
    StrategyRunner,
)

# =============================================================================
# 레거시 호환 (core.py에서)
# =============================================================================
from .core import (
    detect_patterns_macd,
    detect_patterns_adxdi,
    run_backtest,
    run_optimization,
)


__all__ = [
    '__version__',
    # 상수
    'DEFAULT_SLIPPAGE', 'DEFAULT_FEE', 'INITIAL_CAPITAL',
    'TOTAL_COST_ONE_WAY', 'TOTAL_COST_ROUND_TRIP',
    'DEFAULT_TIMEFRAME', 'DEFAULT_METHOD',
    'AVAILABLE_TIMEFRAMES', 'AVAILABLE_METHODS',
    'calculate_grade',
    # 프리셋
    'SANDBOX_PARAMS', 'HYBRID_OPTIMAL_PARAMS', 'LOCAL_V23_PARAMS', 'MAX_PROFIT_PARAMS',
    'FILTER_ATR_OPTIMAL', 'BALANCED_OPTIMAL', 'STABLE_OPTIMAL',
    'ALL_PRESETS', 'get_preset', 'list_presets',
    'load_preset_json', 'save_preset_json', 'get_preset_description',
    # 필터
    'SignalFilter', 'apply_filters',
    # 공통 기반
    'calculate_indicators', 'prepare_data', 'run_backtest_core', 'BaseStrategy',
    # 전략 클래스
    'MACDStrategy', 'ADXDIStrategy', 'get_strategy', 'list_strategies',
    'run_macd_backtest', 'run_macd_optimization',
    'run_adxdi_backtest', 'run_adxdi_optimization',
    # UI 인터페이스
    'run_strategy', 'compare_strategies', 'optimize_strategy',
    'get_available_options', 'format_result_summary', 'format_comparison_summary',
    'StrategyRunner',
    # 레거시
    'detect_patterns_macd', 'detect_patterns_adxdi',
    'run_backtest', 'run_optimization',
]
