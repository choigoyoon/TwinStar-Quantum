"""
TwinStar Quantum - 통합 상수 모듈
================================

Single Source of Truth for all constants.

Usage:
    from config.constants import (
        # 거래소
        EXCHANGE_INFO, SPOT_EXCHANGES, KRW_EXCHANGES,
        # 타임프레임
        TF_MAPPING, TF_RESAMPLE_MAP, TIMEFRAMES,
        # 방향
        DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH,
        # 비용
        SLIPPAGE, FEE, TOTAL_COST,
        # 등급
        GRADE_LIMITS, GRADE_COLORS,
        # 경로
        CACHE_DIR, PRESET_DIR, LOG_DIR,
    )
"""

from .exchanges import (
    EXCHANGE_INFO,
    SPOT_EXCHANGES,
    KRW_EXCHANGES,
    COMMON_KRW_SYMBOLS,
    get_exchange_symbols,
    get_exchange_fees,
    is_spot_exchange,
)

from .timeframes import (
    TF_MAPPING,
    TF_RESAMPLE_MAP,
    TIMEFRAMES,
    normalize_timeframe,
    get_entry_tf,
)

from .trading import (
    # 방향
    DIRECTION_LONG,
    DIRECTION_SHORT,
    DIRECTION_BOTH,
    to_api_direction,
    from_api_direction,
    # 비용
    SLIPPAGE,
    FEE,
    TOTAL_COST,
    # 레버리지
    DEFAULT_LEVERAGE,
    MAX_LEVERAGE,
)

from .grades import (
    GRADE_LIMITS,
    GRADE_COLORS,
    is_coin_allowed,
    get_tier_color,
    get_max_positions,
)

from .paths import (
    CACHE_DIR,
    PRESET_DIR,
    LOG_DIR,
    DATA_DIR,
    CONFIG_DIR,
)

from .presets import (
    generate_preset_filename,
    parse_preset_filename,
    OPTIMIZATION_MODES,
    get_preset_template,
)

__all__ = [
    # 거래소
    'EXCHANGE_INFO', 'SPOT_EXCHANGES', 'KRW_EXCHANGES', 'COMMON_KRW_SYMBOLS',
    'get_exchange_symbols', 'get_exchange_fees', 'is_spot_exchange',
    # 타임프레임
    'TF_MAPPING', 'TF_RESAMPLE_MAP', 'TIMEFRAMES',
    'normalize_timeframe', 'get_entry_tf',
    # 방향
    'DIRECTION_LONG', 'DIRECTION_SHORT', 'DIRECTION_BOTH',
    'to_api_direction', 'from_api_direction',
    # 비용
    'SLIPPAGE', 'FEE', 'TOTAL_COST',
    # 레버리지
    'DEFAULT_LEVERAGE', 'MAX_LEVERAGE',
    # 등급
    'GRADE_LIMITS', 'GRADE_COLORS',
    'is_coin_allowed', 'get_tier_color', 'get_max_positions',
    # 경로
    'CACHE_DIR', 'PRESET_DIR', 'LOG_DIR', 'DATA_DIR', 'CONFIG_DIR',
    # 프리셋
    'generate_preset_filename', 'parse_preset_filename',
    'OPTIMIZATION_MODES', 'get_preset_template',
]

__version__ = '1.0.0'
