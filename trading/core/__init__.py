"""
트레이딩 핵심 모듈
=================

상수, 시그널, 지표 계산

Usage:
    from trading.core import (
        # 상수
        SLIPPAGE, FEE, DIRECTION_LONG, DIRECTION_SHORT,
        # 시그널
        TradeSignal, SignalGenerator,
        # 지표
        calculate_indicators, prepare_data,
    )
"""

# 상수 (constants.py)
from .constants import (
    # 비용
    SLIPPAGE,
    FEE,
    INITIAL_CAPITAL,
    DEFAULT_SLIPPAGE,
    DEFAULT_FEE,
    TOTAL_COST,
    # 타임프레임
    AVAILABLE_TIMEFRAMES,
    TF_MAPPING,
    TF_RESAMPLE_MAP,
    # 방향
    DIRECTION_LONG,
    DIRECTION_SHORT,
    DIRECTION_BOTH,
    to_api_direction,
    from_api_direction,
    # 등급
    calculate_grade,
    # 거래소
    EXCHANGE_INFO,
)

# 프리셋 (presets.py)
from .presets import (
    SANDBOX_PARAMS,
    ALL_PRESETS,
    get_preset,
    list_presets,
    save_preset_json,
    load_preset_json,
    list_preset_files,
)

# 시그널 (signals.py)
from .signals import TradeSignal, SignalGenerator

# 지표 (indicators.py)
from .indicators import (
    calculate_indicators,
    IndicatorSet,
    prepare_data,
    add_indicators_to_df,
    calculate_rsi,
    calculate_ema,
    calculate_macd,
    calculate_atr,
)

__all__ = [
    # 상수
    'SLIPPAGE', 'FEE', 'INITIAL_CAPITAL', 'DEFAULT_SLIPPAGE', 'DEFAULT_FEE', 'TOTAL_COST',
    'AVAILABLE_TIMEFRAMES', 'TF_MAPPING', 'TF_RESAMPLE_MAP',
    'DIRECTION_LONG', 'DIRECTION_SHORT', 'DIRECTION_BOTH',
    'to_api_direction', 'from_api_direction',
    'calculate_grade', 'EXCHANGE_INFO',
    # 프리셋
    'SANDBOX_PARAMS', 'ALL_PRESETS', 'get_preset', 'list_presets',
    'save_preset_json', 'load_preset_json', 'list_preset_files',
    # 시그널
    'TradeSignal', 'SignalGenerator',
    # 지표
    'calculate_indicators', 'IndicatorSet', 'prepare_data', 'add_indicators_to_df',
    'calculate_rsi', 'calculate_ema', 'calculate_macd', 'calculate_atr',
]
