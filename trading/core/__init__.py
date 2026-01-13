"""
Trading Core Module
===================

공통 모듈: 상수, 지표, 필터, 실행 로직, 프리셋

모듈 구조:
    constants.py  - 비용/타임프레임/방향/등급 상수
    indicators.py - 기술적 지표 계산 (ATR, MACD, ADX 등)
    filters.py    - 진입 필터 (Stochastic, Downtrend)
    execution.py  - 거래 시뮬레이션/메트릭 계산
    presets.py    - 파라미터 프리셋 + JSON 저장/로드

v1.8.3 호환 포맷 지원
"""

# =============================================================================
# constants.py - 비용/상수/등급
# =============================================================================
from .constants import (
    # 비용 (기본)
    DEFAULT_SLIPPAGE,
    DEFAULT_FEE,
    INITIAL_CAPITAL,
    # 비용 (v1.8.3 별칭)
    SLIPPAGE,
    FEE,
    TOTAL_COST,
    # 타임프레임
    AVAILABLE_TIMEFRAMES,
    DEFAULT_TIMEFRAME,
    TF_MAPPING,
    TF_RESAMPLE_MAP,
    # 방향
    DIRECTION_LONG,
    DIRECTION_SHORT,
    DIRECTION_BOTH,
    to_api_direction,
    from_api_direction,
    # 전략
    AVAILABLE_STRATEGIES,
    DEFAULT_STRATEGY,
    # 등급
    calculate_grade,
    # 거래소
    EXCHANGE_INFO,
    AVAILABLE_EXCHANGES,
    DEFAULT_EXCHANGE,
)

# =============================================================================
# indicators.py - 지표 계산
# =============================================================================
from .indicators import (
    calculate_indicators,
    prepare_data,
)

# =============================================================================
# filters.py - 진입 필터
# =============================================================================
from .filters import (
    apply_entry_filters,
)

# =============================================================================
# execution.py - 거래 시뮬레이션
# =============================================================================
from .execution import (
    run_simulation,
    calculate_metrics,
)

# =============================================================================
# presets.py - 프리셋 관리
# =============================================================================
from .presets import (
    # 내장 프리셋
    SANDBOX_PARAMS,
    FILTER_ATR_OPTIMAL,
    BALANCED_OPTIMAL,
    STABLE_OPTIMAL,
    HYBRID_OPTIMAL,
    LOCAL_V23_PARAMS,
    MAX_PROFIT_PARAMS,
    ALL_PRESETS,
    # 프리셋 유틸리티
    get_preset,
    list_presets,
    get_preset_description,
    get_preset_info,
    # JSON 저장/로드 (v1.8.3 호환)
    save_preset_json,
    load_preset_json,
    list_preset_files,
)


__all__ = [
    # 비용
    'DEFAULT_SLIPPAGE', 'DEFAULT_FEE', 'INITIAL_CAPITAL',
    'SLIPPAGE', 'FEE', 'TOTAL_COST',
    # 타임프레임
    'AVAILABLE_TIMEFRAMES', 'DEFAULT_TIMEFRAME',
    'TF_MAPPING', 'TF_RESAMPLE_MAP',
    # 방향
    'DIRECTION_LONG', 'DIRECTION_SHORT', 'DIRECTION_BOTH',
    'to_api_direction', 'from_api_direction',
    # 전략/등급/거래소
    'AVAILABLE_STRATEGIES', 'DEFAULT_STRATEGY',
    'calculate_grade',
    'EXCHANGE_INFO', 'AVAILABLE_EXCHANGES', 'DEFAULT_EXCHANGE',
    # 지표
    'calculate_indicators', 'prepare_data',
    # 필터
    'apply_entry_filters',
    # 실행
    'run_simulation', 'calculate_metrics',
    # 프리셋
    'SANDBOX_PARAMS', 'FILTER_ATR_OPTIMAL', 'BALANCED_OPTIMAL',
    'STABLE_OPTIMAL', 'HYBRID_OPTIMAL', 'LOCAL_V23_PARAMS', 'MAX_PROFIT_PARAMS',
    'ALL_PRESETS', 'get_preset', 'list_presets',
    'get_preset_description', 'get_preset_info',
    'save_preset_json', 'load_preset_json', 'list_preset_files',
]
